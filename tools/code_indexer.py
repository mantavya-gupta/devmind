"""
code_indexer.py — Semantic code search for DevMind
Embeds code chunks into Qdrant for intelligent retrieval.
"""

import uuid
import json
from pathlib import Path
from dataclasses import dataclass
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

COLLECTION_PREFIX = "devmind_"
EMBED_MODEL = "all-MiniLM-L6-v2"
VECTOR_SIZE = 384
CHUNK_SIZE = 60   # lines per chunk for non-symbol files


@dataclass
class CodeChunk:
    """A searchable chunk of code with metadata."""
    chunk_id: str
    repo_id: str
    file_path: str
    language: str
    kind: str          # function | class | chunk | file
    name: str
    code: str
    embedding: list[float] = None


_model = None

def _get_model():
    global _model
    if _model is None:
        print("[code_indexer] Loading embedding model...")
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


def _get_client():
    try:
        client = QdrantClient(host="localhost", port=6333)
        client.get_collections()
        return client
    except Exception:
        return QdrantClient(":memory:")


def _make_collection_name(repo_id: str) -> str:
    safe = repo_id.replace("-", "_").replace("/", "_")[:40]
    return f"{COLLECTION_PREFIX}{safe}"


def index_repo(parsed_files: list, repo_id: str) -> QdrantClient:
    """
    Embed and index all parsed files into Qdrant.

    Args:
        parsed_files: Output from code_parser.parse_repo()
        repo_id:      Unique identifier for this repo

    Returns:
        Connected QdrantClient with data loaded
    """
    client = _get_client()
    collection = _make_collection_name(repo_id)
    model = _get_model()

    # Create collection
    existing = [c.name for c in client.get_collections().collections]
    if collection in existing:
        client.delete_collection(collection)
    client.create_collection(
        collection_name=collection,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )

    # Build chunks from parsed files
    chunks = []
    for pf in parsed_files:
        if pf.symbols:
            # Index each symbol separately
            for sym in pf.symbols:
                text = f"{sym.kind} {sym.name} in {pf.file_path}\n{sym.docstring}\n{sym.code}"
                chunks.append(CodeChunk(
                    chunk_id=str(uuid.uuid4()),
                    repo_id=repo_id,
                    file_path=pf.file_path,
                    language=pf.language,
                    kind=sym.kind,
                    name=sym.name,
                    code=sym.code[:1500],
                ))
        else:
            # For files without symbols, chunk by lines
            lines = pf.raw_content.splitlines()
            for i in range(0, len(lines), CHUNK_SIZE):
                chunk_lines = lines[i:i+CHUNK_SIZE]
                chunks.append(CodeChunk(
                    chunk_id=str(uuid.uuid4()),
                    repo_id=repo_id,
                    file_path=pf.file_path,
                    language=pf.language,
                    kind="chunk",
                    name=f"{pf.file_path}:{i+1}-{i+len(chunk_lines)}",
                    code="\n".join(chunk_lines)[:1500],
                ))

    print(f"[code_indexer] Embedding {len(chunks)} code chunks...")

    # Embed in batches
    texts = [f"{c.kind} {c.name}\n{c.code}" for c in chunks]
    batch_size = 64
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        embs = model.encode(batch, normalize_embeddings=True)
        all_embeddings.extend(embs.tolist())
        print(f"[code_indexer] Embedded {min(i+batch_size, len(texts))}/{len(texts)}")

    # Upsert to Qdrant
    points = []
    for chunk, emb in zip(chunks, all_embeddings):
        points.append(PointStruct(
            id=chunk.chunk_id,
            vector=emb,
            payload={
                "repo_id": chunk.repo_id,
                "file_path": chunk.file_path,
                "language": chunk.language,
                "kind": chunk.kind,
                "name": chunk.name,
                "code": chunk.code,
            }
        ))

    for i in range(0, len(points), 100):
        client.upsert(collection_name=collection, points=points[i:i+100])

    print(f"[code_indexer] Indexed {len(points)} chunks into '{collection}'")
    return client, collection


def search_code(query: str, client: QdrantClient, collection: str, top_k: int = 5) -> list[dict]:
    """
    Semantic search over indexed codebase.

    Args:
        query:      Natural language or code query
        client:     Connected Qdrant client
        collection: Collection name for this repo
        top_k:      Number of results to return

    Returns:
        List of matching code chunks with scores
    """
    model = _get_model()
    embedding = model.encode(query, normalize_embeddings=True).tolist()

    results = client.query_points(
        collection_name=collection,
        query=embedding,
        limit=top_k,
        with_payload=True,
    ).points

    return [
        {
            "file_path": r.payload["file_path"],
            "kind": r.payload["kind"],
            "name": r.payload["name"],
            "language": r.payload["language"],
            "code": r.payload["code"],
            "score": round(r.score, 4),
        }
        for r in results
    ]
