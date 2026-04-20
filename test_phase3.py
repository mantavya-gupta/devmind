import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from agent.core.codebase import CodebaseIntelligence
from tools.tool_registry import ToolRegistry
from agent.core.react_agent import DevMindAgent

print("=" * 55)
print("DevMind Phase 3 — ReAct Agent Loop Test")
print("=" * 55)

# Load repo
ci = CodebaseIntelligence()
ci.load_repo("https://github.com/pallets/click")

# Set up tools and agent
tools = ToolRegistry(ci, ci.repo.local_path)
agent = DevMindAgent(tools, ci)

# Give the agent a real task
task = """
Analyze the click library codebase and:
1. Find the main Command class and understand its structure
2. Read the core.py file to understand how commands are processed
3. Write a brief technical summary of how click handles command parsing
4. Create a file called devmind_analysis.md with your findings
"""

result = agent.run(task, verbose=True)

print(f"\n{'='*55}")
print(f"Agent completed in {result['steps']} steps")
print(f"Modified files: {result['modified_files']}")
print(f"Success: {result['success']}")
print(f"\nFinal answer preview:")
print(result['final_answer'][:500])
print("=" * 55)
