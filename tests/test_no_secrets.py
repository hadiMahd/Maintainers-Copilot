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


def test_phase6_spec_artifacts_no_secrets():
    """Assert Phase 6 spec artifacts contain no real secret patterns."""
    feature_dir = PROJECT_ROOT / "specs" / "006-auth-memory-audit"
    if not feature_dir.exists():
        pytest.skip("Phase 6 spec directory does not exist")
    md_files = list(feature_dir.rglob("*.md"))
    assert md_files, "No markdown files found in Phase 6 spec directory"
    for file in md_files:
        content = file.read_text()
        for pattern in SECRET_PATTERNS:
            matches = pattern.findall(content)
            assert not matches, f"Found potential secret in {file}: {matches}"


def test_phase7_prompts_and_spec_artifacts_no_secrets():
    """Assert Phase 7 prompt files and spec artifacts contain no real secrets."""
    prompt_files = list((PROJECT_ROOT / "prompts").glob("chatbot_*.md"))
    spec_files = list((PROJECT_ROOT / "specs" / "007-tool-chatbot-backend").rglob("*.md"))
    for file in prompt_files + spec_files:
        content = file.read_text()
        for pattern in SECRET_PATTERNS:
            matches = pattern.findall(content)
            assert not matches, f"Found potential secret in {file}: {matches}"


def test_no_env_file_committed():
    """Assert .env is ignored by git if it exists at project root."""
    env_file = PROJECT_ROOT / ".env"
    gitignore = PROJECT_ROOT / ".gitignore"
    if env_file.exists():
        assert gitignore.exists(), ".gitignore missing but .env exists"
        gitignore_content = gitignore.read_text()
        assert ".env" in gitignore_content, (
            f".env exists at project root but is not in .gitignore"
        )


def test_label_mapping_yml_no_secrets():
    """Assert label_mapping.yml contains no token/password/key patterns."""
    mapping_file = PROJECT_ROOT / "config" / "label_mapping.yml"
    if not mapping_file.exists():
        pytest.skip("config/label_mapping.yml does not exist")
    content = mapping_file.read_text()
    forbidden_patterns = [
        re.compile(r"token", re.IGNORECASE),
        re.compile(r"password", re.IGNORECASE),
        re.compile(r"secret", re.IGNORECASE),
        re.compile(r"api[_\s]?key", re.IGNORECASE),
        re.compile(r"sk-[A-Za-z0-9]{20,}"),
    ]
    for pattern in forbidden_patterns:
        matches = pattern.findall(content)
        assert not matches, f"Found potential secret pattern in {mapping_file}: {matches}"


def test_dataset_settings_token_not_logged():
    """Assert DatasetSettings with fake token does not leak token in repr."""
    from pydantic import SecretStr
    from config.dataset_settings import DatasetSettings

    settings = DatasetSettings(
        repo_owner="test",
        repo_name="repo",
        github_token=SecretStr("fake-token-12345"),
    )
    repr_str = repr(settings)
    assert "fake-token-12345" not in repr_str, (
        f"Secret token leaked in repr: {repr_str}"
    )
    # Also verify get_secret_value() works
    assert settings.github_token is not None
    assert settings.github_token.get_secret_value() == "fake-token-12345"
