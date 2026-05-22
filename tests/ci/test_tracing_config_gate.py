"""Tests for tracing config validation gate."""

from pathlib import Path

from scripts.ci.tracing_checks import check_tracing_enabled_warning, validate_tracing_config


class TestTracingConfigGate:
    """Verify tracing config validation detects misconfiguration."""

    def test_validate_tracing_config_no_env(self, monkeypatch):
        monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
        monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
        monkeypatch.delenv("LANGSMITH_ENDPOINT", raising=False)
        passed, errors = validate_tracing_config()
        assert passed is False
        assert any("LANGSMITH_API_KEY" in e for e in errors)

    def test_validate_tracing_config_valid(self, monkeypatch):
        monkeypatch.setenv("LANGSMITH_API_KEY", "ls__valid_key_1234567890")
        monkeypatch.setenv("LANGSMITH_PROJECT", "test-project")
        passed, errors = validate_tracing_config()
        assert passed is True
        assert errors == []

    def test_validate_tracing_config_short_key(self, monkeypatch):
        monkeypatch.setenv("LANGSMITH_API_KEY", "short")
        monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
        passed, errors = validate_tracing_config()
        assert passed is False

    def test_validate_tracing_config_endpoint_without_project(self, monkeypatch):
        monkeypatch.setenv("LANGSMITH_API_KEY", "ls__valid_key_1234567890")
        monkeypatch.setenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
        monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
        passed, errors = validate_tracing_config()
        assert passed is False
        assert any("PROJECT" in e for e in errors)

    def test_check_tracing_enabled_warning_fails_on_bad_config(self, monkeypatch):
        monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
        monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
        ok, msg = check_tracing_enabled_warning()
        assert ok is False
        assert "invalid" in msg.lower() or "not set" in msg.lower()

    def test_check_tracing_enabled_warning_passes_on_valid(self, monkeypatch):
        monkeypatch.setenv("LANGSMITH_API_KEY", "ls__valid_key_1234567890")
        monkeypatch.setenv("LANGSMITH_PROJECT", "test")
        ok, msg = check_tracing_enabled_warning()
        assert ok is True

    def test_tracing_script_imports_cleanly(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "validate_tracing", "scripts/ci/validate_tracing.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

    def test_tracing_config_no_paid_credentials(self):
        content = Path("scripts/ci/validate_tracing.py").read_text()
        assert "AZURE_OPENAI_KEY" not in content

    def test_validate_tracing_config_accepts_settings_dict(self, monkeypatch):
        monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
        monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
        passed, errors = validate_tracing_config(
            {"lanesmith_api_key": "ls__test", "lanesmith_project": "test"}
        )
        assert isinstance(passed, bool)
