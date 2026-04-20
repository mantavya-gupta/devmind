import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from agent.core.codebase import CodebaseIntelligence

print("=" * 55)
print("DevMind Phase 1 — Codebase Intelligence Test")
print("=" * 55)

ci = CodebaseIntelligence()

# Load a small real public repo for testing
summary = ci.load_repo("https://github.com/pallets/click")

print(f"\nRepo summary:")
for k, v in summary.items():
    print(f"  {k}: {v}")

print(f"\nFile tree (first 10):")
print(ci.get_file_tree(max_files=10))

print(f"\nSemantic search: 'handle command line arguments'")
results = ci.search("handle command line arguments", top_k=3)
for r in results:
    print(f"\n  [{r['score']}] {r['kind']} '{r['name']}' in {r['file_path']}")
    print(f"  Preview: {r['code'][:100]}...")

print(f"\nSemantic search: 'parse options and flags'")
results = ci.search("parse options and flags", top_k=3)
for r in results:
    print(f"\n  [{r['score']}] {r['kind']} '{r['name']}' in {r['file_path']}")

print("\n" + "=" * 55)
print("Phase 1 complete! Codebase intelligence working.")
print("Next: say 'build Phase 2' for the tool system!")
print("=" * 55)
