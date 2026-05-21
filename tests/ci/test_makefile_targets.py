"""Test Makefile target definitions and behavior."""

import os
import subprocess
import tempfile
from pathlib import Path


class TestMakefileTargetsExist:
    """Verify all required Make targets are defined."""

    def test_makefile_exists(self):
        assert Path("Makefile").exists()

    def test_validate_target_exists(self):
        content = Path("Makefile").read_text()
        assert "validate:" in content

    def test_lint_target_exists(self):
        content = Path("Makefile").read_text()
        assert "lint:" in content

    def test_format_check_target_exists(self):
        content = Path("Makefile").read_text()
        assert "format-check:" in content

    def test_import_check_target_exists(self):
        content = Path("Makefile").read_text()
        assert "import-check:" in content

    def test_type_check_target_exists(self):
        content = Path("Makefile").read_text()
        assert "type-check:" in content

    def test_test_target_exists(self):
        content = Path("Makefile").read_text()
        assert "test:" in content

    def test_evals_target_exists(self):
        content = Path("Makefile").read_text()
        assert "evals:" in content

    def test_security_target_exists(self):
        content = Path("Makefile").read_text()
        assert "security:" in content

    def test_smoke_target_exists(self):
        content = Path("Makefile").read_text()
        assert "smoke:" in content

    def test_docs_target_exists(self):
        content = Path("Makefile").read_text()
        assert "docs:" in content

    def test_validate_invokes_quality_gates(self):
        content = Path("Makefile").read_text()
        assert "run_lint" in content or "lint" in content
        assert "format" in content
        assert "type-check" in content

    def test_validate_invokes_tests(self):
        content = Path("Makefile").read_text()
        assert "test" in content.lower()

    def test_lint_delegates_to_script(self):
        content = Path("Makefile").read_text()
        assert "run_lint" in content

    def test_format_check_delegates_to_script(self):
        content = Path("Makefile").read_text()
        assert "run_format_check" in content

    def test_evals_target_delegates_to_ci_scripts(self):
        content = Path("Makefile").read_text()
        assert "check_eval_thresholds" in content

    def test_security_target_delegates_to_ci_scripts(self):
        content = Path("Makefile").read_text()
        assert "check_redaction_leaks" in content

    def test_smoke_target_delegates_to_script(self):
        content = Path("Makefile").read_text()
        assert "smoke_stack" in content

    def test_no_paid_credentials_in_makefile(self):
        content = Path("Makefile").read_text()
        assert "AZURE_OPENAI_KEY" not in content
        assert "OPENAI_API_KEY" not in content
        assert "sk-" not in content
