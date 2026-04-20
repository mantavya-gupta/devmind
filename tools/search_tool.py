"""
search_tool.py — Code search tool for DevMind agent
Combines semantic search + keyword grep for finding relevant code.
"""

import re
from pathlib import Path


class SearchCodeTool:
    """
    Tool: search_code
    The agent uses this to find relevant functions, classes,
    and code patterns before reading full files.
    """

    name = "search_code"
    description = (
        "Search the codebase for relevant code using natural language or keywords. "
        "Use this first to find which files and functions are relevant "
        "before reading them in detail. "
        "Input: search query string"
    )

    def __init__(self, codebase_intelligence, repo_local_path: str):
        self.ci = codebase_intelligence
        self.repo_path = Path(repo_local_path)

    def semantic_search(self, query: str, top_k: int = 5) -> dict:
        """Search using semantic embeddings."""
        results = self.ci.search(query, top_k=top_k)
        return {
            "success": True,
            "query": query,
            "type": "semantic",
            "results": results,
            "count": len(results),
        }

    def grep(self, pattern: str, file_pattern: str = "*.py") -> dict:
        """Keyword grep across the repository."""
        matches = []
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            regex = re.compile(re.escape(pattern), re.IGNORECASE)

        for file_path in self.repo_path.rglob(file_pattern):
            if any(d in file_path.parts for d in {".git", "__pycache__", "node_modules"}):
                continue
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                for i, line in enumerate(content.splitlines(), 1):
                    if regex.search(line):
                        matches.append({
                            "file": str(file_path.relative_to(self.repo_path)),
                            "line": i,
                            "content": line.strip()[:120],
                        })
                        if len(matches) >= 20:
                            break
            except Exception:
                continue
            if len(matches) >= 20:
                break

        return {
            "success": True,
            "pattern": pattern,
            "type": "grep",
            "results": matches,
            "count": len(matches),
        }

    def run(self, query: str, top_k: int = 5) -> dict:
        """
        Smart search — combines semantic + grep for best results.
        The agent's primary search interface.
        """
        # Semantic search
        semantic = self.semantic_search(query, top_k=top_k)

        # Also grep for exact term if query looks like a function/class name
        grep_results = []
        if len(query.split()) <= 3:
            grep = self.grep(query)
            grep_results = grep["results"][:5]

        return {
            "success": True,
            "query": query,
            "semantic_results": semantic["results"],
            "grep_results": grep_results,
            "total": len(semantic["results"]) + len(grep_results),
        }
