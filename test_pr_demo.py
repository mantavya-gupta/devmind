import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from agent.core.codebase import CodebaseIntelligence
from tools.tool_registry import ToolRegistry
from agent.core.pr_agent import PRAgent

# Use YOUR repo
REPO = "mantavya-gupta/devmind-test-repo"

ci = CodebaseIntelligence()
ci.load_repo(f"https://github.com/{REPO}")
tools = ToolRegistry(ci, ci.repo.local_path)
agent = PRAgent(tools, ci)

task = """
Create a Python file called calculator.py with:
1. An add(a, b) function
2. A subtract(a, b) function
3. A multiply(a, b) function
4. Proper docstrings for each function
5. A simple __main__ block that demos the functions
"""

result = agent.fix_issue(task=task)

print(f"\nSuccess: {result['success']}")
if result.get('pr_url'):
    print(f"PR URL: {result['pr_url']}")
