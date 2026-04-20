import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from agent.core.codebase import CodebaseIntelligence
from tools.tool_registry import ToolRegistry
from agent.core.react_agent import DevMindAgent

ci = CodebaseIntelligence()
ci.load_repo("https://github.com/pallets/click")
tools = ToolRegistry(ci, ci.repo.local_path)
agent = DevMindAgent(tools, ci)

task = """
Find the tests/ directory, pick one test file, read it,
and add a new test function to it that tests something
not already covered. Then run the tests to verify they pass.
"""

result = agent.run(task, verbose=True)
print(f"\nSteps: {result['steps']}")
print(f"Modified: {result['modified_files']}")
