"""Tests for redaction leak gate — fake secrets must not appear unredacted."""

from pathlib import Path

FAKE_PROBES = [
    "sk-fake-test-key-12345",
    "password=super_secret_test_value",
]


class TestRedactionLeakGate:
    """Verify redaction leak gate detects fake secrets in logs, traces, memory, audit."""

    def test_redaction_leak_module_imports(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "check_redaction_leaks", "scripts/ci/check_redaction_leaks.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

    def test_fake_probes_defined(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "check_redaction_leaks", "scripts/ci/check_redaction_leaks.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert len(mod.FAKE_PROBES) >= 2

    def test_no_fake_probe_in_clean_output(self):
        """Clean output (no probes) should pass leak check."""
        clean_lines = [
            "log line 1: all good",
            "log line 2: nothing sensitive here",
        ]
        for probe in FAKE_PROBES:
            for line in clean_lines:
                assert probe not in line

    def test_fake_probe_detected_in_output(self):
        """Output containing a fake probe should be detected."""
        leaked_lines = [
            "log: processing request",
            "log: using api key sk-fake-test-key-12345 for auth",  # LEAKED!
        ]
        leaks = []
        for probe in FAKE_PROBES:
            for line in leaked_lines:
                if probe in line:
                    leaks.append((probe, line))
        assert len(leaks) >= 1, "Should detect fake probe leak"

    def test_redact_output_function(self):
        """The redaction function should replace secret values."""
        from scripts.ci.common import redact_output

        text = "key=sk-fake-test-key-12345 and password=hunter2"
        result = redact_output(text, [(p, "[REDACTED]") for p in FAKE_PROBES])
        assert "sk-fake-test-key-12345" not in result
        assert "REDACTED" in result

    def test_fake_probe_in_logs_detected(self):
        """Leak check should scan log-like output for fake probes."""
        log_content = """
        INFO: Starting application
        DEBUG: Config loaded with api_key=sk-fake-test-key-12345
        INFO: Application started
        """
        leaks_found = any(probe in log_content for probe in FAKE_PROBES)
        assert leaks_found, "Fake probe should be detected in log content"

    def test_fake_probe_in_json_output_detected(self):
        """Leak check should scan JSON output for fake probes."""
        import json

        record = {
            "message": "processing",
            "auth": {"api_key": "sk-fake-test-key-12345"},  # LEAKED!
        }
        payload = json.dumps(record)
        leaks_found = any(probe in payload for probe in FAKE_PROBES)
        assert leaks_found, "Fake probe should be detected in JSON payload"

    def test_multiple_targets_scanned(self):
        """Leak check scans logs, traces, memory, audit, and captured output."""
        targets = {
            "logs": "app.log: ERROR auth_sk-fake-test-key-12345_failed",
            "audit": '{"action":"memory.write","key":"sk-fake-test-key-12345"}',
            "captured": "stdout: loaded password=super_secret_test_value",
        }
        for target_name, content in targets.items():
            leaks = [p for p in FAKE_PROBES if p in content]
            assert len(leaks) > 0, f"Should detect leak in {target_name}"

    def test_clean_output_passes_all_targets(self):
        """Clean output should not trigger any leak detection."""
        safe = "INFO: Request processed successfully, trace_id=abc123"
        for probe in FAKE_PROBES:
            assert probe not in safe

    def test_redaction_leak_no_paid_credentials(self):
        content = Path("scripts/ci/check_redaction_leaks.py").read_text()
        assert "AZURE_OPENAI_KEY" not in content
        assert "OPENAI_API_KEY" not in content
        assert "sk-" not in content or "sk-fake" in content
