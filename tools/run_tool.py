"""
run_tool.py — Code execution tool for DevMind agent
Runs commands in an isolated environment and returns results.
"""

import subprocess
import os
import sys
from pathlib import Path


class RunCommandTool:
    """
    Tool: run_command
    The agent uses this to run tests, linters, and scripts.
    Uses subprocess with timeout for safety.
    No Docker required — runs in isolated subprocess.
    """

    name = "run_command"
    description = (
        "Execute a shell command in the repository directory. "
        "Use this to run tests (pytest), check syntax (python -m py_compile), "
        "or install dependencies. "
        "Input: command string (e.g. 'pytest tests/test_basic.py -v')"
    )

    ALLOWED_COMMANDS = {
        "pytest", "python", "pip", "node", "npm",
        "echo", "cat", "ls", "find", "grep",
        "python3", "flake8", "mypy", "ruff",
    }

    TIMEOUT = 60  # seconds

    def __init__(self, repo_local_path: str):
        self.repo_path = Path(repo_local_path)

    def run(self, command: str) -> dict:
        """
        Execute a command in the repo directory.

        Returns:
            dict with success, stdout, stderr, returncode, command
        """
        command = command.strip().strip('"').strip("'")

        # Safety check
        base_cmd = command.split()[0] if command.split() else ""
        if base_cmd not in self.ALLOWED_COMMANDS:
            return {
                "success": False,
                "error": f"Command '{base_cmd}' not allowed.",
                "allowed": list(self.ALLOWED_COMMANDS),
            }

        # Block dangerous patterns
        dangerous = ["rm -rf", "sudo", "curl", "wget", "> /", "| sh", "| bash"]
        if any(d in command for d in dangerous):
            return {
                "success": False,
                "error": "Dangerous command blocked for safety.",
            }

        print(f"[run_tool] Running: {command}")

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT,
                env={**os.environ, "PYTHONPATH": str(self.repo_path)},
            )

            stdout = result.stdout[-3000:] if result.stdout else ""
            stderr = result.stderr[-2000:] if result.stderr else ""
            success = result.returncode == 0

            print(f"[run_tool] Exit code: {result.returncode}")
            if not success and stderr:
                print(f"[run_tool] Stderr: {stderr[:200]}")

            return {
                "success": success,
                "command": command,
                "stdout": stdout,
                "stderr": stderr,
                "returncode": result.returncode,
                "summary": self._summarize(stdout, stderr, success),
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Command timed out after {self.TIMEOUT}s",
                "command": command,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "command": command,
            }

    def run_tests(self, test_path: str = "tests/", extra_args: str = "-v --tb=short") -> dict:
        """Convenience method to run pytest."""
        return self.run(f"pytest {test_path} -v --tb=short")

    def check_syntax(self, file_path: str) -> dict:
        """Check Python syntax without running."""
        return self.run(f"python -m py_compile {file_path}")

    def install_deps(self) -> dict:
        """Install repo dependencies."""
        if (self.repo_path / "requirements.txt").exists():
            return self.run("pip install -r requirements.txt -q")
        elif (self.repo_path / "pyproject.toml").exists():
            return self.run("pip install -e . -q")
        return {"success": True, "message": "No dependency file found."}

    def _summarize(self, stdout: str, stderr: str, success: bool) -> str:
        """Create a short summary of the execution result."""
        if success:
            lines = stdout.strip().splitlines()
            return lines[-1] if lines else "Command succeeded."
        else:
            lines = (stderr or stdout).strip().splitlines()
            return lines[-1] if lines else "Command failed."
