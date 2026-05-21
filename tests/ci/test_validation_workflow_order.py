"""Test validation workflow order and no-paid-credentials enforcement."""

import yaml
from pathlib import Path


class TestValidationWorkflowOrder:
    """Verify gate ordering matches contract in validation-workflow.md."""

    def test_gate_order_in_run_all(self):
        content = Path("scripts/ci/run_all.sh").read_text()
        order = [
            ("dependency-install", "uv sync"),
            ("lint", "flake8"),
            ("format-check", "black"),
            ("import-check", "isort"),
            ("type-check", "mypy"),
            ("tests", "pytest"),
        ]
        positions = {name: content.find(keyword) for name, keyword in order}
        sorted_positions = sorted(positions.items(), key=lambda x: x[1])
        for i, (name, _) in enumerate(sorted_positions):
            assert name in [item[0] for item in order[i:i+3]], f"Gate {name} out of order"

    def test_run_all_does_fail_fast_pattern(self):
        content = Path("scripts/ci/run_all.sh").read_text()
        assert "FAILED" in content
        assert "FAIL" in content
        assert "exit 1" in content

    def test_run_all_produces_summary(self):
        content = Path("scripts/ci/run_all.sh").read_text()
        assert "Passed" in content
        assert "Failed" in content

    def test_ci_yaml_job_order_matches_contract(self):
        path = Path(".github/workflows/ci.yml")
        with open(path) as f:
            wf = yaml.safe_load(f)

        job_names = list(wf["jobs"].keys())
        assert job_names[0] == "install", "First job should be install"
        assert "lint" in job_names
        assert "format-check" in job_names
        assert "type-check" in job_names
        assert "tests" in job_names

    def test_no_paid_credentials_in_run_all(self):
        content = Path("scripts/ci/run_all.sh").read_text()
        assert "AZURE_OPENAI_KEY" not in content
        assert "OPENAI_API_KEY" not in content


class TestNoPaidCredentials:
    """Verify no paid API credentials in any CI script."""

    def test_no_paid_credentials_in_ci_scripts(self):
        ci_dir = Path("scripts/ci")
        for script in ci_dir.rglob("*.py"):
            if script.name in ("__init__.py", "secret_scan.py", "common.py", "check_redaction_leaks.py", "check_static_secret_patterns.py"):
                continue
            content = script.read_text()
            assert "sk-" not in content, f"{script} contains sk- pattern"
            assert "password=" not in content.lower(), f"{script} contains password= pattern"

    def test_no_real_azure_keys_in_ci(self):
        ci_dir = Path("scripts/ci")
        for script in ci_dir.glob("*.py"):
            if script.name in ("__init__.py", "secret_scan.py"):
                continue
            content = script.read_text()
            assert "AZURE_OPENAI_KEY" not in content, f"{script} references real Azure key"
            assert "OPENAI_API_KEY" not in content, f"{script} references real OpenAI key"

    def test_no_real_azure_keys_in_shell_scripts(self):
        ci_dir = Path("scripts/ci")
        for script in ci_dir.glob("*.sh"):
            content = script.read_text()
            assert "AZURE_OPENAI_KEY" not in content
            assert "OPENAI_API_KEY" not in content

    def test_no_paid_credentials_in_makefile(self):
        content = Path("Makefile").read_text()
        assert "AZURE_OPENAI_KEY" not in content
        assert "OPENAI_API_KEY" not in content

    def test_no_paid_credentials_in_thresholds(self):
        content = Path("evals/eval_thresholds.yaml").read_text()
        assert "AZURE_OPENAI_KEY" not in content
        assert "sk-" not in content


class TestValidationScriptImports:
    """Verify CI scripts import cleanly without side effects."""

    def test_common_module_imports(self):
        from scripts.ci import common

        assert hasattr(common, "run")
        assert hasattr(common, "fail")
        assert hasattr(common, "safe_summary")

    def test_models_module_imports(self):
        from scripts.ci import models

        assert hasattr(models, "GateResult")
        assert hasattr(models, "ValidationRun")

    def test_eval_report_module_imports(self):
        from scripts.ci import eval_report

        assert hasattr(eval_report, "build_report")
        assert hasattr(eval_report, "validate_report")

    def test_thresholds_module_imports(self):
        from scripts.ci import thresholds

        assert hasattr(thresholds, "load_thresholds")
        assert hasattr(thresholds, "check_threshold")

    def test_secret_scan_module_imports(self):
        from scripts.ci import secret_scan

        assert hasattr(secret_scan, "scan_file")
        assert hasattr(secret_scan, "scan_directory")

    def test_model_artifacts_module_imports(self):
        from scripts.ci import model_artifacts

        assert hasattr(model_artifacts, "compute_sha256")
        assert hasattr(model_artifacts, "verify_artifact")

    def test_startup_checks_module_imports(self):
        from scripts.ci import startup_checks

        assert hasattr(startup_checks, "check_vault_unreachable")

    def test_tracing_checks_module_imports(self):
        from scripts.ci import tracing_checks

        assert hasattr(tracing_checks, "validate_tracing_config")

    def test_docs_check_module_imports(self):
        from scripts.ci import docs_check

        assert hasattr(docs_check, "check_docs_exist")
        assert hasattr(docs_check, "check_readme_sections")
