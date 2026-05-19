"""Tests for secret hygiene."""

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent

# Patterns that indicate real secrets
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),  # API keys
]
UUID_PATTERN = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def test_env_example_no_real_credentials():
    """Assert .env.example contains no real secret patterns."""
    env_example = PROJECT_ROOT / ".env.example"
    content = env_example.read_text()
    for pattern in SECRET_PATTERNS:
        matches = pattern.findall(content)
        assert not matches, f"Found potential secret in .env.example: {matches}"
    # Check for UUIDs that aren't prefixed with fake-
    for match in UUID_PATTERN.findall(content):
        assert match.startswith("fake-"), f"Found real-looking UUID in .env.example: {match}"


def test_docs_no_secrets():
    """Assert no .md file in docs/ contains real secret patterns."""
    docs_dir = PROJECT_ROOT / "docs"
    if not docs_dir.exists():
        pytest.skip("docs/ directory does not exist yet")
    md_files = list(docs_dir.rglob("*.md"))
    assert md_files, "No .md files found in docs/"
    for file in md_files:
        content = file.read_text()
        for pattern in SECRET_PATTERNS:
            matches = pattern.findall(content)
            assert not matches, f"Found potential secret in {file}: {matches}"
        for match in UUID_PATTERN.findall(content):
            assert match.startswith("fake-"), f"Found real-looking UUID in {file}: {match}"


def test_no_env_file_committed():
    """Assert .env does not exist at project root."""
    env_file = PROJECT_ROOT / ".env"
    assert not env_file.exists(), (
        f"Real secrets file .env exists at project root: {env_file}"
    )
