"""
pr_agent.py — End-to-end PR creation workflow for DevMind
Extends the ReAct agent with GitHub PR capabilities.
"""

import os
from .react_agent import DevMindAgent
from tools.github_tool import GitHubTool


class PRAgent(DevMindAgent):
    """
    Extends DevMindAgent with the ability to:
    1. Read GitHub issues
    2. Fix the code using the ReAct loop
    3. Create a branch
    4. Commit the changes
    5. Open a real Pull Request
    """

    def __init__(self, tool_registry, codebase_intelligence):
        super().__init__(tool_registry, codebase_intelligence)
        self.github = GitHubTool(
            repo_local_path=codebase_intelligence.repo.local_path,
            repo_full_name=codebase_intelligence.repo.full_name,
        )

    def fix_issue(self, issue_number: int = None, task: str = None) -> dict:
        """
        Full workflow: read issue → fix code → create PR.

        Args:
            issue_number: GitHub issue number to fix (optional)
            task:         Manual task description (if no issue number)

        Returns:
            dict with PR URL, steps taken, modified files
        """
        print("\n" + "="*55)
        print("DevMind PR Agent — Full Workflow")
        print("="*55)

        # Step 1: Get task from issue or manual input
        if issue_number:
            print(f"\n[pr_agent] Reading issue #{issue_number}...")
            issues = self.github.get_repo_issues(limit=50)
            if not issues["success"]:
                print(f"[pr_agent] Could not fetch issues: {issues['error']}")
                task = task or "Improve code quality and add documentation"
            else:
                issue = next(
                    (i for i in issues["issues"] if i["number"] == issue_number),
                    None
                )
                if issue:
                    task = f"Fix GitHub Issue #{issue_number}: {issue['title']}\n\nIssue description: {issue['body']}"
                    print(f"[pr_agent] Issue: {issue['title']}")
                else:
                    task = task or f"Fix issue #{issue_number}"

        if not task:
            task = "Improve code quality, add missing docstrings, and fix any obvious issues"

        # Step 2: Create a branch before making changes
        print(f"\n[pr_agent] Creating branch...")
        branch_result = self.github.create_branch()
        if not branch_result["success"]:
            print(f"[pr_agent] Branch creation failed: {branch_result['error']}")
            print("[pr_agent] Continuing without branch (local only mode)")
        else:
            print(f"[pr_agent] Branch: {branch_result['branch']}")

        # Step 3: Run the ReAct agent loop to complete the task
        print(f"\n[pr_agent] Running agent on task...")
        agent_result = self.run(task, verbose=True)

        if not agent_result["modified_files"]:
            print("\n[pr_agent] No files modified. Skipping PR creation.")
            return {
                "success": False,
                "reason": "Agent did not modify any files",
                "agent_result": agent_result,
            }

        # Step 4: Commit the changes
        print(f"\n[pr_agent] Committing {len(agent_result['modified_files'])} modified files...")
        commit_msg = f"Fix: {task[:60]}..."
        commit_result = self.github.commit_changes(
            message=commit_msg,
            files=agent_result["modified_files"],
        )

        if not commit_result["success"]:
            print(f"[pr_agent] Commit failed: {commit_result['error']}")
            return {
                "success": False,
                "reason": commit_result["error"],
                "agent_result": agent_result,
            }

        print(f"[pr_agent] Committed: {commit_result['commit_sha']}")

        # Step 5: Push the branch
        print(f"\n[pr_agent] Pushing branch to GitHub...")
        push_result = self.github.push_branch()

        if not push_result["success"]:
            print(f"[pr_agent] Push failed: {push_result['error']}")
            print("[pr_agent] Changes committed locally but not pushed.")
            return {
                "success": False,
                "reason": push_result["error"],
                "commit": commit_result,
                "agent_result": agent_result,
            }

        # Step 6: Open Pull Request
        print(f"\n[pr_agent] Opening Pull Request...")
        pr_title = f"Fix: {task[:60]}"
        pr_body = (
            f"## Summary\n\n"
            f"{agent_result['final_answer']}\n\n"
            f"## Changes Made\n\n"
            f"Modified files:\n"
            + "\n".join(f"- `{f}`" for f in agent_result["modified_files"])
            + f"\n\n## Agent Steps\n\n"
            f"Completed in {agent_result['steps']} autonomous steps.\n\n"
            f"## Diff\n\n```\n{self.github.get_diff()}\n```"
        )

        pr_result = self.github.open_pull_request(
            title=pr_title,
            body=pr_body,
        )

        if pr_result["success"]:
            print(f"\n[pr_agent] PR opened successfully!")
            print(f"[pr_agent] URL: {pr_result['pr_url']}")
        else:
            print(f"[pr_agent] PR creation failed: {pr_result.get('error')}")

        return {
            "success": pr_result.get("success", False),
            "pr_url": pr_result.get("pr_url"),
            "pr_number": pr_result.get("pr_number"),
            "branch": self.github.current_branch,
            "commit": commit_result.get("commit_sha"),
            "modified_files": agent_result["modified_files"],
            "agent_steps": agent_result["steps"],
            "final_answer": agent_result["final_answer"],
        }

    def list_issues(self) -> list:
        """List open issues for the user to pick from."""
        result = self.github.get_repo_issues(limit=10)
        if not result["success"]:
            print(f"Could not fetch issues: {result['error']}")
            return []
        return result["issues"]
