"""
codebase.py — Codebase intelligence orchestrator for DevMind
Ties together: clone → parse → index → search
"""

from tools.repo_cloner import clone_repo, ClonedRepo
from tools.code_parser import parse_repo
from tools.code_indexer import index_repo, search_code


class CodebaseIntelligence:
    """
    Main interface for DevMind's codebase understanding.
    The agent uses this to read, search, and understand any GitHub repo.
    """

    def __init__(self):
        self.repo: ClonedRepo = None
        self.parsed_files = []
        self.qdrant_client = None
        self.collection = None

    def load_repo(self, repo_url: str, github_token: str = None) -> dict:
        """
        Full pipeline: clone → parse → index a GitHub repository.

        Returns summary dict with repo stats.
        """
        print(f"\n[DevMind] Loading repository: {repo_url}")
        print("=" * 55)

        # Step 1: Clone
        self.repo = clone_repo(repo_url, github_token)

        # Step 2: Parse
        print(f"\n[DevMind] Parsing {self.repo.file_count} files...")
        self.parsed_files = parse_repo(self.repo)

        # Step 3: Index
        print(f"\n[DevMind] Indexing codebase for semantic search...")
        self.qdrant_client, self.collection = index_repo(
            self.parsed_files, self.repo.repo_id
        )

        summary = {
            "repo": self.repo.full_name,
            "description": self.repo.description,
            "files": self.repo.file_count,
            "total_lines": self.repo.total_lines,
            "languages": self.repo.languages,
            "symbols": sum(len(p.symbols) for p in self.parsed_files),
            "local_path": self.repo.local_path,
        }

        print(f"\n[DevMind] Repository loaded!")
        print(f"  Files:    {summary['files']}")
        print(f"  Lines:    {summary['total_lines']:,}")
        print(f"  Symbols:  {summary['symbols']}")
        print(f"  Languages:{summary['languages']}")
        return summary

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Semantic search over the codebase."""
        if not self.qdrant_client:
            raise RuntimeError("No repo loaded. Call load_repo() first.")
        return search_code(query, self.qdrant_client, self.collection, top_k)

    def read_file(self, relative_path: str) -> str:
        """Read a specific file from the cloned repo."""
        if not self.repo:
            raise RuntimeError("No repo loaded.")
        from pathlib import Path
        full_path = Path(self.repo.local_path) / relative_path
        if not full_path.exists():
            return f"File not found: {relative_path}"
        return full_path.read_text(encoding="utf-8", errors="ignore")

    def get_file_tree(self, max_files: int = 50) -> str:
        """Return a compact file tree for the agent's context."""
        if not self.repo:
            return "No repo loaded."
        lines = [f"Repository: {self.repo.full_name}"]
        for f in self.repo.files[:max_files]:
            lines.append(f"  {f.relative_path} ({f.language}, {f.content.count(chr(10))+1} lines)")
        if self.repo.file_count > max_files:
            lines.append(f"  ... and {self.repo.file_count - max_files} more files")
        return "\n".join(lines)
