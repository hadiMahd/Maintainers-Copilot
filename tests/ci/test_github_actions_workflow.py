"""Test CI workflow structure in .github/workflows/ci.yml."""

from pathlib import Path

import pytest
import yaml


class TestGitHubActionsWorkflow:
    """Verify ci.yml structure and required gates."""

    @pytest.fixture(autouse=True)
    def _workflow(self):
        path = Path(".github/workflows/ci.yml")
        assert path.exists(), "ci.yml not found"
        with open(path) as f:
            self.wf = yaml.safe_load(f)

    def test_workflow_has_name(self):
        assert "name" in self.wf

    def test_workflow_runs_on_push(self):
        """YAML 'on' key is parsed as True (YAML 1.1 bool)."""
        trigger_config = self.wf.get(True)  # 'on' maps to True in YAML
        assert trigger_config is not None, "workflow has no trigger configuration"

    def test_workflow_has_jobs(self):
        assert "jobs" in self.wf
        assert len(self.wf["jobs"]) > 0

    def test_install_job_exists(self):
        assert "install" in self.wf["jobs"]

    def test_lint_job_exists(self):
        assert "lint" in self.wf["jobs"]

    def test_format_check_job_exists(self):
        assert "format-check" in self.wf["jobs"]

    def test_type_check_job_exists(self):
        assert "type-check" in self.wf["jobs"]

    def test_tests_job_exists(self):
        assert "tests" in self.wf["jobs"]

    def test_threshold_validation_job_exists(self):
        assert "threshold-validation" in self.wf["jobs"]

    def test_classifier_eval_job_exists(self):
        assert "classifier-eval" in self.wf["jobs"]

    def test_rag_eval_job_exists(self):
        assert "rag-eval" in self.wf["jobs"]

    def test_redaction_leak_job_exists(self):
        assert "redaction-leak" in self.wf["jobs"]

    def test_static_secret_grep_job_exists(self):
        assert "static-secret-grep" in self.wf["jobs"]

    def test_model_artifacts_job_exists(self):
        assert "model-artifacts" in self.wf["jobs"]

    def test_startup_failures_job_exists(self):
        assert "startup-failures" in self.wf["jobs"]

    def test_tracing_config_job_exists(self):
        assert "tracing-config" in self.wf["jobs"]

    def test_docker_build_job_exists(self):
        assert "docker-build" in self.wf["jobs"]

    def test_stack_smoke_job_exists(self):
        assert "stack-smoke" in self.wf["jobs"]

    def test_eval_report_job_exists(self):
        assert "eval-report" in self.wf["jobs"]

    def test_previous_green_diff_job_exists(self):
        assert "previous-green-diff" in self.wf["jobs"]

    def test_report_storage_job_exists(self):
        assert "report-storage" in self.wf["jobs"]

    def test_docs_validation_job_exists(self):
        assert "docs-validation" in self.wf["jobs"]

    def test_docker_build_is_non_skippable(self):
        """Docker build must be a required, non-skippable gate."""
        job = self.wf["jobs"]["docker-build"]
        assert "if" not in job, "docker-build should not have a conditional skip"

    def test_stack_smoke_depends_on_docker_build(self):
        job = self.wf["jobs"]["stack-smoke"]
        needs = job.get("needs", [])
        assert "docker-build" in needs

    def test_no_paid_credentials_in_workflow(self):
        content = Path(".github/workflows/ci.yml").read_text()
        assert "AZURE_OPENAI_KEY" not in content
        assert "OPENAI_API_KEY" not in content

    def test_install_uses_uv(self):
        job = self.wf["jobs"]["install"]
        steps = job.get("steps", [])
        assert len(steps) > 0
        has_uv = any("uv" in str(s) for s in steps)
        assert has_uv, "install should use uv"

    def test_install_smoke_import_uses_existing_domain_export(self):
        job = self.wf["jobs"]["install"]
        steps = job.get("steps", [])
        install_commands = [str(step.get("run", "")) for step in steps if isinstance(step, dict)]
        smoke_commands = [cmd for cmd in install_commands if "python -c" in cmd]

        assert smoke_commands, "install should include a Python import smoke check"
        assert all("from app.domain import settings" not in cmd for cmd in smoke_commands)
        assert any("from app.domain import DomainError" in cmd for cmd in smoke_commands)

    def test_test_job_uses_pytest(self):
        job = self.wf["jobs"]["tests"]
        steps = job.get("steps", [])
        has_pytest = any("pytest" in str(s) for s in steps)
        assert has_pytest, "tests should use pytest"
