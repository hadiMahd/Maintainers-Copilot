"""Tests for runbook failure-path coverage."""

from pathlib import Path


class TestRunbookFailurePaths:
    """Verify runbook covers CI failure debugging for all gates."""

    def test_runbook_exists_and_has_content(self):
        assert Path("docs/runbook.md").exists()
        size = Path("docs/runbook.md").stat().st_size
        assert size >= 500, f"runbook is {size} bytes"

    def test_runbook_covers_lint_failures(self):
        content = Path("docs/runbook.md").read_text().lower()
        assert "lint" in content or "flake8" in content

    def test_runbook_covers_type_check_failures(self):
        content = Path("docs/runbook.md").read_text().lower()
        assert "type" in content or "mypy" in content

    def test_runbook_covers_eval_failures(self):
        content = Path("docs/runbook.md").read_text().lower()
        assert "eval" in content or "threshold" in content

    def test_runbook_covers_vault_failures(self):
        content = Path("docs/runbook.md").read_text().lower()
        assert "vault" in content

    def test_runbook_covers_docker_smoke_failures(self):
        content = Path("docs/runbook.md").read_text().lower()
        assert "smoke" in content or "docker" in content

    def test_runbook_covers_model_artifact_failures(self):
        content = Path("docs/runbook.md").read_text().lower()
        assert "artifact" in content or "model" in content

    def test_runbook_covers_tracing_failures(self):
        content = Path("docs/runbook.md").read_text().lower()
        assert "tracing" in content or "langsmith" in content

    def test_runbook_covers_health_check(self):
        content = Path("docs/runbook.md").read_text().lower()
        assert "health" in content

    def test_runbook_has_start_stack(self):
        content = Path("docs/runbook.md").read_text()
        assert "docker compose" in content or "docker-compose" in content

    def test_runbook_has_test_commands(self):
        content = Path("docs/runbook.md").read_text()
        assert "pytest" in content

    def test_runbook_no_paid_credentials(self):
        content = Path("docs/runbook.md").read_text()
        assert "AZURE_OPENAI_KEY" not in content
