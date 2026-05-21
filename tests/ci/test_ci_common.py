"""Unit tests for safe command output redaction in CI common helpers."""

from scripts.ci.common import (
    env_bool,
    fail,
    pass_gate,
    redact_output,
    safe_summary,
)


class TestSafeSummary:
    def test_short_output_returned_unchanged(self):
        lines = ["line 1", "line 2"]
        result = safe_summary(lines)
        assert result == "line 1\nline 2"

    def test_long_output_truncated(self):
        lines = [f"line {i}" for i in range(20)]
        result = safe_summary(lines, max_lines=5)
        assert "more lines" in result
        assert "line 0" in result
        assert "line 19" not in result


class TestRedactOutput:
    def test_redact_secret_patterns(self):
        text = "api_key=sk-12345 and password=secret"
        patterns = [
            ("sk-12345", "[REDACTED]"),
            ("secret", "[REDACTED]"),
        ]
        result = redact_output(text, patterns)
        assert "sk-12345" not in result
        assert "[REDACTED]" in result

    def test_no_patterns_no_change(self):
        text = "hello world"
        result = redact_output(text, [])
        assert result == text


class TestFailAndPass:
    def test_fail_exits(self):
        try:
            fail("test failure")
            assert False, "Should have raised SystemExit"
        except SystemExit as e:
            assert e.code == 1

    def test_fail_custom_code(self):
        try:
            fail("test failure", code=42)
            assert False, "Should have raised SystemExit"
        except SystemExit as e:
            assert e.code == 42

    def test_pass_gate_does_not_exit(self):
        pass_gate("all good")


class TestEnvBool:
    def test_true_values(self, monkeypatch):
        for val in ("1", "true", "yes", "on"):
            monkeypatch.setenv("TEST_VAR", val)
            assert env_bool("TEST_VAR") is True

    def test_false_values(self, monkeypatch):
        for val in ("0", "false", "no", "off"):
            monkeypatch.setenv("TEST_VAR", val)
            assert env_bool("TEST_VAR") is False

    def test_unset_returns_default(self, monkeypatch):
        monkeypatch.delenv("TEST_VAR", raising=False)
        assert env_bool("TEST_VAR", default=True) is True
        assert env_bool("TEST_VAR", default=False) is False
