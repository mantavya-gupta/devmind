"""
github_tool.py — GitHub integration for DevMind
Creates branches, commits changes, opens Pull Requests.
"""

import os
import git
from pathlib import Path
from datetime import datetime
from github import Github, GithubException


class GitHubTool:
    """
    Tool: github
    The agent uses this to create branches, commit fixes,
    and open Pull Requests on GitHub.
    """

    def __init__(self, repo_local_path: str, repo_full_name: str):
        self.repo_path = Path(repo_local_path)
        self.repo_full_name = repo_full_name
        self.token = os.getenv("GITHUB_TOKEN")
        self.gh = Github(self.token) if self.token else None
        self.git_repo = git.Repo(repo_local_path)
        self.current_branch = None

    def create_branch(self, branch_name: str = None) -> dict:
        """Create a new branch for the agent's changes."""
        if not branch_name:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            branch_name = f"devmind/fix_{ts}"

        try:
            # Create and checkout new branch
            new_branch = self.git_repo.create_head(branch_name)
            new_branch.checkout()
            self.current_branch = branch_name
            print(f"[github_tool] Created branch: {branch_name}")
            return {
                "success": True,
                "branch": branch_name,
                "message": f"Created and checked out branch '{branch_name}'",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def commit_changes(self, message: str, files: list[str] = None) -> dict:
        """Stage and commit the agent's changes."""
        try:
            # Stage files
            if files:
                for f in files:
                    self.git_repo.index.add([f])
            else:
                # Stage all modified files
                self.git_repo.git.add(A=True)

            # Check if there's anything to commit
            if not self.git_repo.index.diff("HEAD"):
                return {
                    "success": False,
                    "error": "No changes to commit.",
                }

            # Commit
            commit = self.git_repo.index.commit(
                f"[DevMind] {message}",
                author=git.Actor("DevMind Agent", "devmind@ai.agent"),
                committer=git.Actor("DevMind Agent", "devmind@ai.agent"),
            )
            print(f"[github_tool] Committed: {commit.hexsha[:8]}")
            return {
                "success": True,
                "commit_sha": commit.hexsha[:8],
                "message": message,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def push_branch(self) -> dict:
        """Push the current branch to GitHub."""
        if not self.current_branch:
            return {"success": False, "error": "No branch created yet."}
        if not self.token:
            return {"success": False, "error": "GITHUB_TOKEN not set."}

        try:
            # Set remote URL with token for auth
            remote_url = f"https://{self.token}@github.com/{self.repo_full_name}.git"
            origin = self.git_repo.remote("origin")
            origin.set_url(remote_url)

            # Push
            origin.push(self.current_branch)
            print(f"[github_tool] Pushed branch: {self.current_branch}")
            return {
                "success": True,
                "branch": self.current_branch,
                "message": f"Pushed '{self.current_branch}' to GitHub",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_pull_request(
        self,
        title: str,
        body: str,
        base_branch: str = "main",
    ) -> dict:
        """Open a Pull Request on GitHub."""
        if not self.gh:
            return {"success": False, "error": "GitHub token not configured."}
        if not self.current_branch:
            return {"success": False, "error": "No branch to PR from."}

        try:
            gh_repo = self.gh.get_repo(self.repo_full_name)

            # Try main, then master as base
            try:
                gh_repo.get_branch(base_branch)
            except GithubException:
                base_branch = "master"

            pr = gh_repo.create_pull(
                title=f"[DevMind] {title}",
                body=(
                    f"## DevMind AI Agent\n\n"
                    f"{body}\n\n"
                    f"---\n"
                    f"*This PR was automatically created by [DevMind](https://github.com/mantavya-gupta/devmind)*"
                ),
                head=self.current_branch,
                base=base_branch,
            )
            print(f"[github_tool] PR opened: {pr.html_url}")
            return {
                "success": True,
                "pr_number": pr.number,
                "pr_url": pr.html_url,
                "title": pr.title,
                "branch": self.current_branch,
            }
        except GithubException as e:
            return {"success": False, "error": f"GitHub API error: {e.data}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_repo_issues(self, limit: int = 10) -> dict:
        """Fetch open issues from the repository."""
        if not self.gh:
            return {"success": False, "error": "GitHub token not configured."}
        try:
            gh_repo = self.gh.get_repo(self.repo_full_name)
            issues = list(gh_repo.get_issues(state="open"))[:limit]
            return {
                "success": True,
                "issues": [
                    {
                        "number": i.number,
                        "title": i.title,
                        "body": (i.body or "")[:300],
                        "labels": [l.name for l in i.labels],
                        "url": i.html_url,
                    }
                    for i in issues
                ],
                "count": len(issues),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def comment_on_issue(self, issue_number: int, comment: str) -> dict:
        """Post a comment on a GitHub issue."""
        if not self.gh:
            return {"success": False, "error": "GitHub token not configured."}
        try:
            gh_repo = self.gh.get_repo(self.repo_full_name)
            issue = gh_repo.get_issue(issue_number)
            comment_obj = issue.create_comment(
                f"**DevMind Agent Update:**\n\n{comment}"
            )
            return {
                "success": True,
                "comment_url": comment_obj.html_url,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_file_from_github(self, file_path: str) -> dict:
        """Fetch a file directly from GitHub API."""
        if not self.gh:
            return {"success": False, "error": "GitHub token not configured."}
        try:
            gh_repo = self.gh.get_repo(self.repo_full_name)
            content = gh_repo.get_contents(file_path)
            return {
                "success": True,
                "content": content.decoded_content.decode("utf-8"),
                "sha": content.sha,
                "path": file_path,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_diff(self) -> str:
        """Get current git diff for PR description."""
        try:
            diff = self.git_repo.git.diff("HEAD~1", "HEAD", stat=True)
            return diff or "No diff available."
        except Exception:
            return "No diff available."
