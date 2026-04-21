# DevMind — AI Software Engineering Agent

> An autonomous AI agent that reads GitHub repositories, plans fixes, writes code, runs tests, and opens real Pull Requests.

## Live Demo

Real PR opened by DevMind: https://github.com/mantavya-gupta/devmind-test-repo/pull/1

## What it does

Give DevMind a GitHub repo URL and a task. It autonomously:
1. Clones and indexes the entire codebase with semantic search
2. Plans a solution using chain-of-thought reasoning
3. Reads relevant files to understand the code
4. Writes the fix or feature
5. Runs tests to verify correctness
6. Creates a branch, commits, and opens a Pull Request

## Architecture

Codebase Intelligence -> ReAct Agent Loop -> Tool System -> GitHub PR

ReAct Loop: THOUGHT -> ACTION -> OBSERVATION -> repeat until done

## Key Technical Features

| Feature | Implementation |
|---------|---------------|
| Codebase indexing | AST parsing + sentence-transformers embeddings |
| Semantic search | Qdrant vector store (384d) |
| Agent loop | ReAct pattern with chain-of-thought planning |
| LLM | LLaMA-3.3-70b via Groq API (free) |
| Tools | read_file, write_file, search_code, run_command, apply_patch |
| Code execution | Subprocess sandbox with timeout |
| GitHub integration | PyGithub + GitPython |
| PR creation | Automatic branch, commit, push, PR |

## Quick Start

    git clone https://github.com/mantavya-gupta/devmind
    cd devmind
    pip install -r requirements.txt
    export GROQ_API_KEY=your-key
    export GITHUB_TOKEN=your-token
    python test_phase4.py

## Example

    from agent.core.codebase import CodebaseIntelligence
    from tools.tool_registry import ToolRegistry
    from agent.core.pr_agent import PRAgent

    ci = CodebaseIntelligence()
    ci.load_repo("https://github.com/youruser/yourrepo")
    tools = ToolRegistry(ci, ci.repo.local_path)
    agent = PRAgent(tools, ci)

    result = agent.fix_issue(task="Add docstrings to all functions in utils.py")
    print(result["pr_url"])

## Agent in action

The agent runs a full ReAct loop:

    [Step 1] THOUGHT: I need to find relevant files first
             ACTION: search_code("utility functions")
             OBSERVATION: Found utils.py with 15 functions

    [Step 2] THOUGHT: Let me read the file to understand it
             ACTION: read_file("utils.py")
             OBSERVATION: File read, 3 functions missing docstrings

    [Step 3] THOUGHT: I will add docstrings now
             ACTION: write_file("utils.py", updated_content)
             OBSERVATION: Successfully wrote utils.py

    [Step 4] THOUGHT: Let me verify the syntax is correct
             ACTION: check_syntax("utils.py")
             OBSERVATION: Syntax OK

    FINAL_ANSWER: Added docstrings to 3 functions. PR opened.

## Tech Stack

Python 3.11, Groq LLaMA3, Qdrant, sentence-transformers, PyGithub, GitPython, FastAPI

## Author

Built by Mantavya Gupta — autonomous AI coding agent with real GitHub PR integration.
