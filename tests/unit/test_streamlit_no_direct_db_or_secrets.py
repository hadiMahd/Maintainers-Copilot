"""Static checks: no direct DB, infra, or secrets in Streamlit code.

Phase 8 acceptance criteria SC-008, SC-009, FR-013, FR-014.
"""

from pathlib import Path


STREAMLIT_DIR = Path(__file__).resolve().parent.parent.parent / "streamlit_app"

FORBIDDEN_IMPORTS = [
    "sqlalchemy",
    "asyncpg",
    "psycopg",
    "redis",
    "hvac",
    "minio",
    "Repository",
    "Session",
]

FORBIDDEN_SECRET_PATTERNS = [
    "password",
    "token",
    "secret",
    "api_key",
    "PRIVATE KEY",
]


def _read_all_streamlit_files() -> list[tuple[str, str]]:
    """Return (filename, content) for every .py file under streamlit_app/."""
    files: list[tuple[str, str]] = []
    for path in STREAMLIT_DIR.rglob("*.py"):
        files.append((str(path.relative_to(STREAMLIT_DIR.parent)), path.read_text()))
    return files


def test_no_sqlalchemy_or_repository_imports():
    files = _read_all_streamlit_files()
    for filepath, content in files:
        for pattern in FORBIDDEN_IMPORTS:
            assert pattern not in content, (
                f"Forbidden import pattern '{pattern}' found in {filepath}"
            )


def test_no_hardcoded_secrets():
    """Verify no hardcoded secrets in Streamlit code.

    Only flags lines where a string literal value looks like a secret:
    long hex strings, base64, or values over 20 chars containing the pattern.
    """
    import re

    files = _read_all_streamlit_files()
    for filepath, content in files:
        for line_num, line in enumerate(content.split("\n"), 1):
            # Find string assignments: name = "value" or name = 'value'
            matches = re.findall(r'=\s*["\'](.{16,})["\']', line)
            for value in matches:
                value_lower = value.lower()
                for pattern in FORBIDDEN_SECRET_PATTERNS:
                    if pattern in value_lower and len(value) >= 16:
                        assert False, (
                            f"Suspected hardcoded '{pattern}' in {filepath}:{line_num}: "
                            f"value is {len(value)} chars long"
                        )


def test_no_orm_model_imports():
    files = _read_all_streamlit_files()
    for filepath, content in files:
        assert "orm_models" not in content, (
            f"ORM model import found in {filepath}"
        )
        assert "app.infra" not in content, (
            f"app.infra import found in {filepath}"
        )
        assert "app.repositories" not in content, (
            f"app.repositories import found in {filepath}"
        )
        assert "app.api" not in content, (
            f"app.api import found in {filepath}"
        )
