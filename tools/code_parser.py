"""
code_parser.py — AST-based code analysis for DevMind
Extracts functions, classes, imports, and call graph from source files.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CodeSymbol:
    """A function, class, or method extracted from source code."""
    name: str
    kind: str           # function | class | method | import
    file_path: str
    line_start: int
    line_end: int
    code: str           # Full source of the symbol
    docstring: str
    calls: list[str] = field(default_factory=list)  # Functions this symbol calls


@dataclass
class ParsedFile:
    """Analysis results for a single source file."""
    file_path: str
    language: str
    symbols: list[CodeSymbol]
    imports: list[str]
    raw_content: str
    line_count: int


def _extract_python_symbols(content: str, file_path: str) -> list[CodeSymbol]:
    """Extract functions and classes from Python source using regex."""
    symbols = []
    lines = content.splitlines()

    # Match function and class definitions
    pattern = re.compile(
        r'^(?P<indent>\s*)(?P<kind>def|class)\s+(?P<name>\w+)',
        re.MULTILINE
    )

    for match in pattern.finditer(content):
        kind = "function" if match.group("kind") == "def" else "class"
        name = match.group("name")
        indent = len(match.group("indent"))

        # Find line number
        line_start = content[:match.start()].count("\n") + 1

        # Find end of block by tracking indentation
        line_end = line_start
        for i in range(line_start, len(lines)):
            if i == line_start - 1:
                continue
            line = lines[i]
            if line.strip() == "":
                continue
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= indent and line.strip():
                line_end = i
                break
        else:
            line_end = len(lines)

        code_block = "\n".join(lines[line_start-1:line_end])

        # Extract docstring
        docstring = ""
        doc_match = re.search(r'"""(.*?)"""', code_block, re.DOTALL)
        if doc_match:
            docstring = doc_match.group(1).strip()[:200]

        # Extract function calls within this block
        calls = re.findall(r'\b(\w+)\s*\(', code_block)
        calls = [c for c in calls if c not in ("def", "class", "if", "for", "while", "return")]

        symbols.append(CodeSymbol(
            name=name,
            kind=kind,
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            code=code_block[:2000],  # Cap at 2000 chars
            docstring=docstring,
            calls=list(set(calls))[:20],
        ))

    return symbols


def _extract_imports(content: str, language: str) -> list[str]:
    """Extract import statements from source code."""
    imports = []
    if language == "Python":
        for match in re.finditer(r'^(?:import|from)\s+(.+?)(?:\s+import.+)?$', content, re.MULTILINE):
            imports.append(match.group(0).strip())
    elif language in ("JavaScript", "TypeScript"):
        for match in re.finditer(r'^(?:import|require)\s*[({]?.*?[)}]?\s*(?:from\s+)?[\'"](.+?)[\'"]', content, re.MULTILINE):
            imports.append(match.group(0).strip()[:100])
    return imports[:30]


def parse_file(file_path: str, content: str, language: str) -> ParsedFile:
    """
    Parse a source file and extract symbols and imports.

    Args:
        file_path: Path to the file (for reference)
        content:   Raw file content
        language:  Programming language

    Returns:
        ParsedFile with extracted symbols and imports
    """
    symbols = []

    if language == "Python":
        symbols = _extract_python_symbols(content, file_path)
    # More languages can be added here

    imports = _extract_imports(content, language)

    return ParsedFile(
        file_path=file_path,
        language=language,
        symbols=symbols,
        imports=imports,
        raw_content=content,
        line_count=content.count("\n") + 1,
    )


def parse_repo(cloned_repo) -> list[ParsedFile]:
    """Parse all files in a cloned repository."""
    parsed = []
    for repo_file in cloned_repo.files:
        if repo_file.language in ("Python", "JavaScript", "TypeScript"):
            pf = parse_file(
                repo_file.relative_path,
                repo_file.content,
                repo_file.language,
            )
            parsed.append(pf)
        else:
            # For other languages, just store without symbol extraction
            parsed.append(ParsedFile(
                file_path=repo_file.relative_path,
                language=repo_file.language,
                symbols=[],
                imports=[],
                raw_content=repo_file.content,
                line_count=repo_file.content.count("\n") + 1,
            ))

    total_symbols = sum(len(p.symbols) for p in parsed)
    print(f"[code_parser] Parsed {len(parsed)} files, {total_symbols} symbols extracted")
    return parsed
