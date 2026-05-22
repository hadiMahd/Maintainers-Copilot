"""Static secret pattern scanner helpers (API key prefix, password patterns)."""

from pathlib import Path
from typing import Optional

UNSAFE_PATTERNS = [
    ("sk-", "API key prefix (OpenAI-style)"),
    ("password=", "Hardcoded password assignment"),
    ("passwd=", "Hardcoded password variant"),
    ("SECRET_KEY=", "Hardcoded secret key"),
]


def scan_file(
    path: Path, patterns: Optional[list[tuple[str, str]]] = None
) -> list[tuple[int, str, str]]:
    """Scan a file for secret patterns. Returns list of (line_number, pattern, line_snippet)."""
    pats = patterns or UNSAFE_PATTERNS
    hits: list[tuple[int, str, str]] = []
    try:
        with open(path) as f:
            for lineno, line in enumerate(f, 1):
                for pat, desc in pats:
                    if pat in line:
                        hits.append((lineno, pat, line.strip()[:120]))
    except (OSError, UnicodeDecodeError):
        pass
    return hits


def scan_directory(
    root: Path,
    exclude_dirs: Optional[set[str]] = None,
    exclude_extensions: Optional[set[str]] = None,
) -> list[tuple[Path, int, str, str]]:
    """Scan a directory tree for secret patterns. Returns (path, lineno, pattern, snippet)."""
    exclude_dirs = exclude_dirs or {
        ".git",
        ".venv",
        "__pycache__",
        "node_modules",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
    }
    exclude_extensions = exclude_extensions or {
        ".pyc",
        ".png",
        ".jpg",
        ".gif",
        ".svg",
        ".woff",
        ".ttf",
        ".gz",
        ".zip",
        ".tar",
        ".ico",
    }
    results: list[tuple[Path, int, str, str]] = []
    for item in root.rglob("*"):
        if item.is_dir():
            continue
        if any(ed in item.parts for ed in exclude_dirs):
            continue
        if item.suffix in exclude_extensions:
            continue
        hits = scan_file(item)
        for lineno, pat, snippet in hits:
            results.append((item, lineno, pat, snippet))
    return results


def is_allowlisted(path: Path, pattern: str, snippet: str) -> bool:
    """Check if a hit should be allowlisted (false positive)."""
    path_str = str(path)
    if ".flake8" in path_str:
        return True
    if "AGENTS.md" in path_str:
        return True
    if "constitution.md" in path_str:
        return True
    if "ci.yml" in path_str and "password" in pattern.lower():
        return True
    if "secret_scan.py" in path_str:
        return True
    if "check_static_secret_patterns.py" in path_str:
        return True
    return False
