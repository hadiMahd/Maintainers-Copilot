"""Tests for documentation completeness — required docs and sections."""

from pathlib import Path

from scripts.ci.docs_check import (
    REQUIRED_DOCS,
    check_docs_exist,
    check_docs_sections,
    check_readme_sections,
    validate_all_docs,
)


class TestDocsCompleteness:
    """Verify all required Phase 10 documentation exists and has content."""

    def test_required_docs_list_complete(self):
        required = REQUIRED_DOCS
        assert "README.md" in required
        assert "docs/architecture.md" in required
        assert "docs/decisions.md" in required
        assert "docs/runbook.md" in required
        assert "docs/evals.md" in required
        assert "docs/security.md" in required

    def test_readme_exists(self):
        assert Path("README.md").exists()

    def test_architecture_doc_exists(self):
        assert Path("docs/architecture.md").exists()

    def test_decisions_doc_exists(self):
        assert Path("docs/decisions.md").exists()

    def test_runbook_doc_exists(self):
        assert Path("docs/runbook.md").exists()

    def test_evals_doc_exists(self):
        assert Path("docs/evals.md").exists()

    def test_security_doc_exists(self):
        assert Path("docs/security.md").exists()

    def test_all_docs_exist(self):
        passed, errors = check_docs_exist()
        assert passed, f"Missing docs: {errors}"

    def test_all_docs_have_content(self):
        passed, errors = check_docs_sections()
        assert passed, f"Docs too short: {errors}"

    def test_readme_has_setup_section(self):
        passed, errors = check_readme_sections()
        assert passed, f"README missing sections: {errors}"

    def test_each_required_doc_over_200_bytes(self):
        for doc in REQUIRED_DOCS:
            path = Path(doc)
            if path.exists():
                size = path.stat().st_size
                assert size >= 200, f"{doc} is only {size} bytes (expected >= 200)"

    def test_validate_all_docs_passes(self):
        passed, results = validate_all_docs()
        assert passed, f"Doc validation failed: {results}"

    def test_docs_no_paid_credentials(self):
        content = Path("scripts/ci/validate_docs.py").read_text()
        assert "AZURE_OPENAI_KEY" not in content
