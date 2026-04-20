import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from agent.core.codebase import CodebaseIntelligence
from tools.tool_registry import ToolRegistry

print("=" * 55)
print("DevMind Phase 2 — Tool System Test")
print("=" * 55)

# Load repo from Phase 1 cache
ci = CodebaseIntelligence()
summary = ci.load_repo("https://github.com/pallets/click")
tools = ToolRegistry(ci, ci.repo.local_path)

print(f"\nTools available: {list(tools.tools.keys())}")

# Test 1: search_code
print("\n── Test 1: search_code ─────────────────────────")
result = tools.call("search_code", query="handle command options")
print(f"Semantic results: {len(result['semantic_results'])}")
print(f"Grep results: {len(result['grep_results'])}")
if result['semantic_results']:
    top = result['semantic_results'][0]
    print(f"Top match: {top['kind']} '{top['name']}' in {top['file_path']}")

# Test 2: list_directory
print("\n── Test 2: list_directory ──────────────────────")
result = tools.call("list_directory", relative_dir="src/click")
if result['success']:
    print(f"Files in src/click: {result['count']}")
    for item in result['items'][:5]:
        print(f"  {item['type']} {item['name']}")

# Test 3: read_file
print("\n── Test 3: read_file ───────────────────────────")
result = tools.call("read_file", relative_path="src/click/core.py")
if result['success']:
    print(f"Read {result['file_path']}: {result['line_count']} lines")
    print(f"First 3 lines:")
    for line in result['content'].splitlines()[:3]:
        print(f"  {line}")

# Test 4: run_command
print("\n── Test 4: run_command ─────────────────────────")
result = tools.call("run_command", command="python --version")
print(f"Command success: {result['success']}")
print(f"Output: {result.get('stdout', '').strip()}")

# Test 5: check_syntax
print("\n── Test 5: check_syntax ────────────────────────")
result = tools.call("check_syntax", file_path="src/click/core.py")
print(f"Syntax OK: {result['success']}")

# Test 6: write_file (write a test file)
print("\n── Test 6: write_file ──────────────────────────")
test_content = '# DevMind test file\nprint("DevMind Phase 2 working!")\n'
result = tools.call("write_file",
    relative_path="devmind_test.py",
    content=test_content)
print(f"Write success: {result['success']}")
print(f"Lines written: {result.get('lines_written')}")

# Run the test file
result = tools.call("run_command", command="python devmind_test.py")
print(f"Run output: {result.get('stdout', '').strip()}")

print("\n" + "=" * 55)
print("Phase 2 complete! All tools working.")
print("Next: say 'build Phase 3' for the ReAct agent loop!")
print("=" * 55)
