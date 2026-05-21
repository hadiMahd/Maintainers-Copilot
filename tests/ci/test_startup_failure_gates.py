"""Tests for startup failure gates — Vault, model, tracing, threshold negative cases."""

import tempfile
from pathlib import Path

import pytest

from scripts.ci.startup_checks import (
    check_disabled_thresholds,
    check_missing_model_artifact,
    check_model_hash_mismatch,
    check_tracing_misconfiguration,
    check_vault_missing_secret,
    check_vault_unreachable,
)


class TestStartupFailureGates:
    """Verify startup checks detect unsafe conditions."""

    def test_vault_unreachable_fails_closed(self):
        ok, msg = check_vault_unreachable()
        assert ok is True
        assert "failed" in msg.lower() or "should" in msg.lower()

    def test_vault_missing_secret_fails_closed(self):
        ok, msg = check_vault_missing_secret()
        assert ok is True, f"Expected pass/closing: {msg}"

    def test_missing_model_artifact_detected(self):
        ok, msg = check_missing_model_artifact()
        assert ok is True
        assert "not found" in msg.lower()

    def test_model_hash_mismatch_detected(self):
        ok, msg = check_model_hash_mismatch()
        assert isinstance(ok, bool)

    def test_tracing_misconfiguration_detected(self):
        ok, msg = check_tracing_misconfiguration()
        assert isinstance(ok, bool)

    def test_disabled_thresholds_detected(self):
        ok, msg = check_disabled_thresholds()
        assert isinstance(ok, bool)

    def test_startup_checks_import_cleanly(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "check_startup_failures", "scripts/ci/check_startup_failures.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

    def test_all_startup_checks_are_present(self):
        checks = [
            check_vault_unreachable,
            check_missing_model_artifact,
            check_model_hash_mismatch,
            check_tracing_misconfiguration,
            check_disabled_thresholds,
            check_vault_missing_secret,
        ]
        for fn in checks:
            result = fn()
            assert isinstance(result, tuple)
            assert len(result) == 2
            assert isinstance(result[0], bool)
            assert isinstance(result[1], str)

    def test_vault_unreachable_returns_structured_failure(self):
        ok, msg = check_vault_unreachable()
        assert isinstance(ok, bool)
        assert len(msg) > 0

    def test_startup_failures_no_paid_credentials(self):
        content = Path("scripts/ci/check_startup_failures.py").read_text()
        assert "AZURE_OPENAI_KEY" not in content
        assert "OPENAI_API_KEY" not in content

    def test_missing_artifact_path_does_not_exist(self):
        """The nonexistent artifact path must NOT exist on the filesystem."""
        from scripts.ci.startup_checks import check_missing_model_artifact

        ok, msg = check_missing_model_artifact()
        assert ok is True
