"""
repo_cloner.py — Clone and index any GitHub repository
DevMind Phase 1: Codebase Intelligence
"""

import os
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from github import Github
import git

REPOS_DIR = Path.home() / "devmind" / "data" / "repos"
SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go",
    ".rs", ".cpp", ".c", ".h", ".cs", ".rb", ".php",
    ".swift", ".kt", ".scala", ".r", ".sh", ".yaml",
    ".yml", ".json", ".toml", ".md", ".txt"
}
IGNORED_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv",
    "venv", "env", "dist", "build", ".next", "vendor",
    ".pytest_cache", "coverage", ".mypy_cache"
}


@dataclass
class RepoFile:
    """A single file from the repository."""
    path: str
    relative_path: str
    extension: str
    content: str
    size_bytes: int
    language: str


@dataclass
class ClonedRepo:
    """A fully cloned and indexed repository."""
    repo_id: str
    full_name: str
    url: str
    local_path: str
    default_branch: str
    description: str
    files: list[RepoFile] = field(default_factory=list)
    file_count: int = 0
    total_lines: int = 0
    languages: dict = field(default_factory=dict)
    cloned_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


LANGUAGE_MAP = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".jsx": "JavaScript", ".tsx": "TypeScript", ".java": "Java",
    ".go": "Go", ".rs": "Rust", ".cpp": "C++", ".c": "C",
    ".h": "C/C++", ".cs": "C#", ".rb": "Ruby", ".php": "PHP",
    ".swift": "Swift", ".kt": "Kotlin", ".scala": "Scala",
    ".r": "R", ".sh": "Shell", ".md": "Markdown",
}


def clone_repo(repo_url: str, github_token: str = None) -> ClonedRepo:
    """
    Clone a GitHub repository and read all its source files.

    Args:
        repo_url:     Full GitHub URL or 'owner/repo' format
        github_token: Optional GitHub token for private repos

    Returns:
        ClonedRepo with all files loaded into memory
    """
    # Parse repo name
    if "github.com" in repo_url:
        full_name = repo_url.rstrip("/").split("github.com/")[-1]
        full_name = full_name.replace(".git", "")
    else:
        full_name = repo_url

    repo_id = full_name.replace("/", "_")
    local_path = REPOS_DIR / repo_id

    print(f"[repo_cloner] Cloning {full_name}...")

    # Get repo metadata from GitHub API
    gh = Github(github_token or os.getenv("GITHUB_TOKEN"))
    try:
        gh_repo = gh.get_repo(full_name)
        description = gh_repo.description or ""
        default_branch = gh_repo.default_branch
        clone_url = gh_repo.clone_url
    except Exception as e:
        print(f"[repo_cloner] GitHub API error: {e}. Using URL directly.")
        description = ""
        default_branch = "main"
        clone_url = f"https://github.com/{full_name}.git"

    # Clone or update local copy
    if local_path.exists():
        print(f"[repo_cloner] Repo already exists locally. Pulling latest...")
        try:
            repo = git.Repo(local_path)
            repo.remotes.origin.pull()
        except Exception:
            shutil.rmtree(local_path)
            git.Repo.clone_from(clone_url, local_path, depth=1)
    else:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"[repo_cloner] Cloning to {local_path}...")
        git.Repo.clone_from(clone_url, local_path, depth=1)

    # Read all source files
    print(f"[repo_cloner] Reading source files...")
    files = []
    language_counts = {}

    for file_path in local_path.rglob("*"):
        # Skip ignored directories
        if any(ignored in file_path.parts for ignored in IGNORED_DIRS):
            continue
        if not file_path.is_file():
            continue
        if file_path.suffix not in SUPPORTED_EXTENSIONS:
            continue

        # Skip very large files (>500KB)
        size = file_path.stat().st_size
        if size > 500_000:
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            relative = str(file_path.relative_to(local_path))
            ext = file_path.suffix
            lang = LANGUAGE_MAP.get(ext, "Other")

            files.append(RepoFile(
                path=str(file_path),
                relative_path=relative,
                extension=ext,
                content=content,
                size_bytes=size,
                language=lang,
            ))
            language_counts[lang] = language_counts.get(lang, 0) + 1

        except Exception as e:
            print(f"[repo_cloner] Skipping {file_path}: {e}")

    total_lines = sum(f.content.count("\n") for f in files)

    print(f"[repo_cloner] Done: {len(files)} files, {total_lines:,} lines")
    print(f"[repo_cloner] Languages: {language_counts}")

    return ClonedRepo(
        repo_id=repo_id,
        full_name=full_name,
        url=repo_url,
        local_path=str(local_path),
        default_branch=default_branch,
        description=description,
        files=files,
        file_count=len(files),
        total_lines=total_lines,
        languages=language_counts,
    )
