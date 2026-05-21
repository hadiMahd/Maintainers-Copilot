"""Reusable command runner and safe output helpers for CI scripts."""

import os
import subprocess
import sys
from typing import Optional


def run(cmd: str, cwd: Optional[str] = None, check: bool = True) -> int:
    """Run a shell command and return the exit code."""
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if check and result.returncode != 0:
        raise SystemExit(result.returncode)
    return result.returncode


def run_capture(cmd: str, cwd: Optional[str] = None) -> tuple[int, str, str]:
    """Run a shell command and capture stdout/stderr."""
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def safe_summary(lines: list[str], max_lines: int = 10) -> str:
    """Return a bounded summary of output lines, truncating if needed."""
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[:max_lines]) + f"\n... ({len(lines) - max_lines} more lines)"


def redact_output(text: str, patterns: list[tuple[str, str]]) -> str:
    """Replace sensitive patterns with [REDACTED] in text."""
    for match_pattern, replacement in patterns:
        text = text.replace(match_pattern, replacement)
    return text


def fail(message: str, code: int = 1) -> None:
    """Print a safe failure message and exit."""
    safe = _sanitize_for_output(message)
    print(f"FAIL: {safe}", file=sys.stderr)
    raise SystemExit(code)


def pass_gate(message: str) -> None:
    """Print a safe pass message."""
    safe = _sanitize_for_output(message)
    print(f"PASS: {safe}")


def _sanitize_for_output(text: str) -> str:
    """Sanitize text for safe public output."""
    secret_patterns = [
        ("sk-", "[SK]"),
        ("password", "[PWD]"),
        ("api_key", "[KEY]"),
        ("secret", "[SECRET]"),
    ]
    result = text
    for pattern, replacement in secret_patterns:
        result = result.replace(pattern, replacement)
    return result


def env_bool(name: str, default: bool = False) -> bool:
    val = os.environ.get(name, str(default)).lower()
    return val in ("1", "true", "yes", "on")
