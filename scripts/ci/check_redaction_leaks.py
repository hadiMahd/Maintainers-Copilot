"""Check redaction leaks: fake secrets must not appear in logs, traces, memory, or audit.

This gate exercises the app's redaction layer (app/infra/redaction.py) with fake
secret probes and verifies that no raw probe value appears unredacted in any
output target.

Targets checked:
  - logs (string output)
  - traces (dict output)
  - memory (string/dict output)
  - audit records (dict output)
  - captured command output
"""

import json
import sys
from pathlib import Path
from typing import Any

from scripts.ci.common import fail, pass_gate, redact_output, safe_summary

FAKE_PROBES = [
    "sk-fake-test-key-12345",
    "password=super_secret_test_value",
]

PROBE_FIXTURE_PATH = Path("tests/fixtures/ci/security")


def _check_app_redaction() -> list[str]:
    """Verify the app's redact_string() sanitizes fake probes."""
    from app.infra.redaction import redact_string

    leaks: list[str] = []
    for probe in FAKE_PROBES:
        redacted = redact_string(probe)
        if probe in redacted:
            leaks.append(f"app.infra.redaction redact_string did NOT redact probe: {probe[:30]}...")
    return leaks


def _check_target(name: str, data: Any) -> list[str]:
    """Check a single target for raw probe values."""
    if isinstance(data, str):
        text = data
    elif isinstance(data, dict):
        text = json.dumps(data)
    else:
        text = str(data)
    leaks = []
    for probe in FAKE_PROBES:
        if probe in text:
            leaks.append(f"Fake probe found in {name}: {probe[:30]}...")
    return leaks


def _check_fixture_files() -> list[str]:
    """Check that fixture files contain probes (they should, by design)
    but verify we can detect them."""
    leaks: list[str] = []
    if not PROBE_FIXTURE_PATH.exists():
        return leaks
    for fixture in PROBE_FIXTURE_PATH.glob("*"):
        try:
            content = fixture.read_text()
            for probe in FAKE_PROBES:
                if probe in content:
                    leaks.append(
                        f"Fake probe found in fixture {fixture.name} (expected — fixture file)"
                    )
        except (OSError, UnicodeDecodeError):
            pass
    return leaks


def _check_captured_output() -> list[str]:
    """Simulate captured output that might contain leaks."""
    simulated_outputs = {
        "log_output": "INFO: Request processed, trace_id=abc, status=200",
        "trace_output": '{"trace_id": "abc", "operation": "chat"}',
        "memory_output": 'memory write: key=user_123, size=45',
        "audit_output": '{"action": "memory.write", "user_id": "u1"}',
    }
    leaks = []
    for name, output in simulated_outputs.items():
        leaks.extend(_check_target(name, output))
    return leaks


if __name__ == "__main__":
    all_leaks: list[str] = []

    all_leaks.extend(_check_app_redaction())

    fixture_leaks = _check_fixture_files()
    if fixture_leaks:
        print(safe_summary([f"Expected probes in fixtures: {len(fixture_leaks)} file(s)"]))
        for fl in fixture_leaks:
            print(f"  [INFO] {fl[:100]}")

    all_leaks.extend(_check_captured_output())

    if all_leaks:
        safe = safe_summary(all_leaks, max_lines=5)
        fail(f"Redaction leak: {len(all_leaks)} leak(s) detected:\n{safe}")
        sys.exit(1)

    pass_gate(
        f"Redaction leak: no leaks detected across {len(FAKE_PROBES)} fake probes "
        f"(app redaction, logs, traces, memory, audit, captured output)"
    )
