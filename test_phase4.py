import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from agent.core.codebase import CodebaseIntelligence
from tools.tool_registry import ToolRegistry
from agent.core.pr_agent import PRAgent

print("=" * 55)
print("DevMind Phase 4 — GitHub PR Integration Test")
print("=" * 55)

# Load repo
ci = CodebaseIntelligence()
ci.load_repo("https://github.com/pallets/click")
tools = ToolRegistry(ci, ci.repo.local_path)
agent = PRAgent(tools, ci)

# List open issues first
print("\nFetching open issues from pallets/click...")
issues = agent.list_issues()
if issues:
    print(f"\nOpen issues ({len(issues)}):")
    for i in issues[:5]:
        print(f"  #{i['number']}: {i['title']}")
else:
    print("No issues fetched (may need token with repo access)")

# Run agent with a manual task (no issue number needed)
task = """
Read the file src/click/utils.py and add proper docstrings
to any functions that are missing them.
Keep the docstrings concise and accurate.
"""

print(f"\nRunning PR agent on task...")
result = agent.fix_issue(task=task)

print(f"\n{'='*55}")
print(f"Result:")
print(f"  Success:        {result['success']}")
print(f"  Modified files: {result.get('modified_files', [])}")
print(f"  Agent steps:    {result.get('agent_steps', 0)}")
if result.get('pr_url'):
    print(f"  PR URL:         {result['pr_url']}")
elif result.get('commit'):
    print(f"  Commit:         {result['commit']} (local only)")
print("=" * 55)
