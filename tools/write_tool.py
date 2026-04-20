"""
write_tool.py — File writing tool for DevMind agent
Allows the agent to create and modify files.
"""

import shutil
from pathlib import Path
from datetime import datetime


class WriteFileTool:
    """
    Tool: write_file
    The agent uses this to write fixes, new code, or tests.
    Always creates a backup before modifying existing files.
    """

    name = "write_file"
    description = (
        "Write or modify a file in the repository. "
        "Use this after planning your fix to implement the changes. "
        "Input: relative file path and new content. "
        "Always reads the file first before modifying it."
    )

    def __init__(self, repo_local_path: str):
        self.repo_path = Path(repo_local_path)
        self.backup_dir = self.repo_path / ".devmind_backups"
        self.backup_dir.mkdir(exist_ok=True)
        self.modified_files = []

    def run(self, relative_path: str, content: str) -> dict:
        """
        Write content to a file, creating a backup first.

        Returns:
            dict with success, file_path, lines_written, backed_up
        """
        relative_path = relative_path.strip().strip('"').strip("'")
        full_path = self.repo_path / relative_path

        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Backup existing file
        backed_up = False
        if full_path.exists():
            timestamp = datetime.now().strftime("%H%M%S")
            backup_name = f"{relative_path.replace('/', '_')}_{timestamp}.bak"
            shutil.copy2(full_path, self.backup_dir / backup_name)
            backed_up = True

        try:
            full_path.write_text(content, encoding="utf-8")
            self.modified_files.append(relative_path)

            return {
                "success": True,
                "file_path": relative_path,
                "lines_written": content.count("\n") + 1,
                "size_bytes": len(content.encode()),
                "backed_up": backed_up,
                "message": f"Successfully wrote {relative_path}",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def apply_patch(self, relative_path: str, old_code: str, new_code: str) -> dict:
        """
        Apply a targeted patch — replace specific code block with new code.
        Safer than rewriting entire files.
        """
        relative_path = relative_path.strip()
        full_path = self.repo_path / relative_path

        if not full_path.exists():
            return {"success": False, "error": f"File not found: {relative_path}"}

        content = full_path.read_text(encoding="utf-8", errors="ignore")

        if old_code not in content:
            return {
                "success": False,
                "error": "Could not find the code to replace.",
                "hint": "Make sure old_code exactly matches the file content.",
            }

        new_content = content.replace(old_code, new_code, 1)

        # Backup and write
        timestamp = datetime.now().strftime("%H%M%S")
        backup_name = f"{relative_path.replace('/', '_')}_{timestamp}.bak"
        shutil.copy2(full_path, self.backup_dir / backup_name)
        full_path.write_text(new_content, encoding="utf-8")
        self.modified_files.append(relative_path)

        return {
            "success": True,
            "file_path": relative_path,
            "patch_applied": True,
            "lines_changed": abs(new_code.count("\n") - old_code.count("\n")),
        }

    def restore_backup(self, relative_path: str) -> dict:
        """Restore a file to its backed-up version."""
        backups = sorted(self.backup_dir.glob(
            f"{relative_path.replace('/', '_')}*.bak"
        ))
        if not backups:
            return {"success": False, "error": "No backup found."}

        latest = backups[-1]
        full_path = self.repo_path / relative_path
        shutil.copy2(latest, full_path)
        return {"success": True, "restored_from": str(latest)}

    def get_diff(self, relative_path: str) -> str:
        """Get a simple diff of current vs backup."""
        import difflib
        full_path = self.repo_path / relative_path
        backups = sorted(self.backup_dir.glob(
            f"{relative_path.replace('/', '_')}*.bak"
        ))
        if not backups or not full_path.exists():
            return "No diff available."
        original = backups[0].read_text(encoding="utf-8", errors="ignore")
        current = full_path.read_text(encoding="utf-8", errors="ignore")
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            current.splitlines(keepends=True),
            fromfile=f"original/{relative_path}",
            tofile=f"modified/{relative_path}",
        )
        return "".join(list(diff)[:100])
