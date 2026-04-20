"""
tool_registry.py — Central registry of all DevMind agent tools
"""

from .read_tool import ReadFileTool
from .write_tool import WriteFileTool
from .run_tool import RunCommandTool
from .search_tool import SearchCodeTool


class ToolRegistry:
    """
    Manages all tools available to the DevMind agent.
    The agent calls tools by name with arguments.
    """

    def __init__(self, codebase_intelligence, repo_local_path: str):
        self.repo_path = repo_local_path
        self.ci = codebase_intelligence

        # Initialize all tools
        self.read = ReadFileTool(repo_local_path)
        self.write = WriteFileTool(repo_local_path)
        self.run = RunCommandTool(repo_local_path)
        self.search = SearchCodeTool(codebase_intelligence, repo_local_path)

        # Tool map for agent to call by name
        self.tools = {
            "read_file": self.read.run,
            "list_directory": self.read.list_directory,
            "write_file": self.write.run,
            "apply_patch": self.write.apply_patch,
            "run_command": self.run.run,
            "run_tests": self.run.run_tests,
            "check_syntax": self.run.check_syntax,
            "search_code": self.search.run,
            "grep": self.search.grep,
        }

        # Tool descriptions for the agent's system prompt
        self.tool_descriptions = [
            {
                "name": "read_file",
                "description": "Read a file from the repository",
                "input": "relative_path: str",
            },
            {
                "name": "list_directory",
                "description": "List files in a directory",
                "input": "relative_dir: str (optional, default=''))",
            },
            {
                "name": "search_code",
                "description": "Semantic + keyword search over codebase",
                "input": "query: str",
            },
            {
                "name": "write_file",
                "description": "Write or overwrite a file with new content",
                "input": "relative_path: str, content: str",
            },
            {
                "name": "apply_patch",
                "description": "Replace a specific code block in a file",
                "input": "relative_path: str, old_code: str, new_code: str",
            },
            {
                "name": "run_command",
                "description": "Run a shell command (pytest, python, etc.)",
                "input": "command: str",
            },
            {
                "name": "run_tests",
                "description": "Run pytest on the repository",
                "input": "test_path: str (optional)",
            },
            {
                "name": "check_syntax",
                "description": "Check Python syntax of a file",
                "input": "file_path: str",
            },
        ]

    def call(self, tool_name: str, **kwargs) -> dict:
        """Call a tool by name with keyword arguments."""
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
                "available_tools": list(self.tools.keys()),
            }
        try:
            result = self.tools[tool_name](**kwargs)
            return result
        except TypeError as e:
            return {
                "success": False,
                "error": f"Wrong arguments for {tool_name}: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Tool {tool_name} failed: {e}",
            }

    def get_descriptions_for_prompt(self) -> str:
        """Format tool descriptions for the agent's system prompt."""
        lines = ["Available tools:"]
        for t in self.tool_descriptions:
            lines.append(f"  - {t['name']}({t['input']}): {t['description']}")
        return "\n".join(lines)
