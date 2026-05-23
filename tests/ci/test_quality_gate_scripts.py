"""Test quality gate wrapper scripts exist and are executable."""

import os
import stat
from pathlib import Path


class TestQualityGateScriptsExist:
    """Verify all required quality gate shell scripts exist."""

    def test_run_lint_sh_exists(self):
        assert Path("scripts/ci/run_lint.sh").exists()

    def test_run_format_check_sh_exists(self):
        assert Path("scripts/ci/run_format_check.sh").exists()

    def test_run_type_check_sh_exists(self):
        assert Path("scripts/ci/run_type_check.sh").exists()

    def test_run_tests_sh_exists(self):
        assert Path("scripts/ci/run_tests.sh").exists()

    def test_run_all_sh_exists(self):
        assert Path("scripts/ci/run_all.sh").exists()

    def test_smoke_stack_sh_exists(self):
        assert Path("scripts/ci/smoke_stack.sh").exists()

    def test_check_eval_thresholds_py_exists(self):
        assert Path("scripts/ci/check_eval_thresholds.py").exists()

    def test_check_redaction_leaks_py_exists(self):
        assert Path("scripts/ci/check_redaction_leaks.py").exists()

    def test_check_static_secret_patterns_py_exists(self):
        assert Path("scripts/ci/check_static_secret_patterns.py").exists()

    def test_check_model_artifacts_py_exists(self):
        assert Path("scripts/ci/check_model_artifacts.py").exists()

    def test_check_startup_failures_py_exists(self):
        assert Path("scripts/ci/check_startup_failures.py").exists()

    def test_validate_tracing_py_exists(self):
        assert Path("scripts/ci/validate_tracing.py").exists()

    def test_validate_docs_py_exists(self):
        assert Path("scripts/ci/validate_docs.py").exists()

    def test_run_evals_sh_exists(self):
        assert Path("scripts/ci/run_evals.sh").exists()


class TestQualityGateScriptsExecutable:
    """Verify shell scripts are executable."""

    def test_run_lint_sh_executable(self):
        st = os.stat("scripts/ci/run_lint.sh")
        assert st.st_mode & stat.S_IXUSR

    def test_run_format_check_sh_executable(self):
        st = os.stat("scripts/ci/run_format_check.sh")
        assert st.st_mode & stat.S_IXUSR

    def test_run_type_check_sh_executable(self):
        st = os.stat("scripts/ci/run_type_check.sh")
        assert st.st_mode & stat.S_IXUSR

    def test_run_tests_sh_executable(self):
        st = os.stat("scripts/ci/run_tests.sh")
        assert st.st_mode & stat.S_IXUSR

    def test_run_all_sh_executable(self):
        st = os.stat("scripts/ci/run_all.sh")
        assert st.st_mode & stat.S_IXUSR


class TestQualityGateScriptContent:
    """Verify script content follows contract."""

    def test_run_lint_uses_flake8(self):
        content = Path("scripts/ci/run_lint.sh").read_text()
        assert "flake8" in content

    def test_run_format_check_uses_black(self):
        content = Path("scripts/ci/run_format_check.sh").read_text()
        assert "black" in content

    def test_run_format_check_uses_isort(self):
        content = Path("scripts/ci/run_format_check.sh").read_text()
        assert "isort" in content

    def test_run_type_check_uses_mypy(self):
        content = Path("scripts/ci/run_type_check.sh").read_text()
        assert "mypy" in content

    def test_run_tests_uses_pytest(self):
        content = Path("scripts/ci/run_tests.sh").read_text()
        assert "pytest" in content

    def test_run_all_includes_all_gates(self):
        content = Path("scripts/ci/run_all.sh").read_text()
        required = [
            "lint",
            "format-check",
            "type-check",
            "tests",
            "threshold",
            "eval",
            "redaction",
            "secret",
            "model-artifact",
            "startup",
            "tracing",
            "docker-build",
            "smoke",
            "eval-report",
            "green",
            "report-storage",
            "docs",
        ]
        for gate in required:
            assert gate in content, f"run_all.sh missing gate: {gate}"
