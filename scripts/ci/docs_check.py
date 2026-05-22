"""Documentation completeness helper."""

from pathlib import Path
from typing import Optional

REQUIRED_DOCS = [
    "README.md",
    "docs/architecture.md",
    "docs/decisions.md",
    "docs/runbook.md",
    "docs/evals.md",
    "docs/security.md",
]

README_SECTIONS = [
    ("setup", ["setup", "install", "installation", "getting started"]),
    ("architecture", ["architecture", "overview"]),
    ("commands", ["command", "make ", "uv run"]),
    ("demo", ["demo", "example"]),
]


def check_docs_exist(base_path: Optional[Path] = None) -> tuple[bool, list[str]]:
    """Check that all required docs exist."""
    base = base_path or Path(".")
    errors: list[str] = []
    for doc in REQUIRED_DOCS:
        if not (base / doc).exists():
            errors.append(f"Missing doc: {doc}")
    return len(errors) == 0, errors


def check_readme_sections(base_path: Optional[Path] = None) -> tuple[bool, list[str]]:
    """Check README.md contains required sections."""
    base = base_path or Path(".")
    readme = base / "README.md"
    errors: list[str] = []
    if not readme.exists():
        return False, ["README.md does not exist"]
    content = readme.read_text().lower()
    for section_name, keywords in README_SECTIONS:
        found = any(kw.lower() in content for kw in keywords)
        if not found:
            errors.append(f"README missing section: {section_name}")
    return len(errors) == 0, errors


def check_docs_sections(base_path: Optional[Path] = None) -> tuple[bool, list[str]]:
    """Check all required docs have content (non-empty)."""
    base = base_path or Path(".")
    errors: list[str] = []
    for doc in REQUIRED_DOCS:
        path = base / doc
        if path.exists() and path.stat().st_size < 50:
            errors.append(f"Doc too short (<50 bytes): {doc}")
    return len(errors) == 0, errors


def validate_all_docs(base_path: Optional[Path] = None) -> tuple[bool, dict[str, str]]:
    """Run all documentation checks. Returns (passed, gate_results)."""
    gate_results: dict[str, str] = {}
    all_passed = True

    passed, errors = check_docs_exist(base_path)
    gate_results["docs_exist"] = "PASS" if passed else "; ".join(errors)
    all_passed = all_passed and passed

    passed, errors = check_readme_sections(base_path)
    gate_results["readme_sections"] = "PASS" if passed else "; ".join(errors)
    all_passed = all_passed and passed

    passed, errors = check_docs_sections(base_path)
    gate_results["docs_sections"] = "PASS" if passed else "; ".join(errors)
    all_passed = all_passed and passed

    return all_passed, gate_results
