"""
read_tool.py — File reading tool for DevMind agent
Allows the agent to read any file in the repository.
"""

from pathlib import Path


class ReadFileTool:
    """
    Tool: read_file
    The agent uses this to read source files, tests, configs.
    """

    name = "read_file"
    description = (
        "Read the contents of a file in the repository. "
        "Use this to understand existing code before making changes. "
        "Input: relative file path (e.g. 'src/main.py')"
    )

    def __init__(self, repo_local_path: str):
        self.repo_path = Path(repo_local_path)

    def run(self, relative_path: str) -> dict:
        """
        Read a file from the repository.

        Returns:
            dict with success, content, line_count, file_path
        """
        relative_path = relative_path.strip().strip('"').strip("'")
        full_path = self.repo_path / relative_path

        if not full_path.exists():
            # Try fuzzy match — find closest file name
            matches = list(self.repo_path.rglob(f"*{Path(relative_path).name}"))
            if matches:
                full_path = matches[0]
                relative_path = str(full_path.relative_to(self.repo_path))
            else:
                return {
                    "success": False,
                    "error": f"File not found: {relative_path}",
                    "suggestion": self._find_similar(relative_path),
                }

        if full_path.stat().st_size > 1_000_000:
            return {
                "success": False,
                "error": f"File too large to read: {relative_path}",
            }

        try:
            content = full_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()

            # Add line numbers for the agent
            numbered = "\n".join(f"{i+1:4d} | {line}" for i, line in enumerate(lines))

            return {
                "success": True,
                "file_path": relative_path,
                "content": numbered,
                "raw_content": content,
                "line_count": len(lines),
                "size_bytes": full_path.stat().st_size,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _find_similar(self, path: str) -> str:
        """Find files with similar names for helpful error messages."""
        name = Path(path).stem
        matches = list(self.repo_path.rglob(f"*{name}*"))[:3]
        if matches:
            return f"Did you mean: {[str(m.relative_to(self.repo_path)) for m in matches]}"
        return "No similar files found."

    def list_directory(self, relative_dir: str = "") -> dict:
        """List files in a directory."""
        dir_path = self.repo_path / relative_dir
        if not dir_path.exists():
            return {"success": False, "error": f"Directory not found: {relative_dir}"}

        items = []
        for item in sorted(dir_path.iterdir()):
            if item.name.startswith("."):
                continue
            items.append({
                "name": item.name,
                "type": "dir" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
            })

        return {
            "success": True,
            "directory": relative_dir or "/",
            "items": items,
            "count": len(items),
        }
