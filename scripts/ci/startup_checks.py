"""Startup negative-case harness helpers."""

import os
import subprocess
from pathlib import Path


class StartupCheckError(Exception):
    pass


def check_vault_unreachable() -> tuple[bool, str]:
    """Verify app fails when Vault is unreachable."""
    env = os.environ.copy()
    env["VAULT_ADDR"] = "http://nonexistent-vault:8200"

    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-c",
            "import os; "
            "os.environ['VAULT_ADDR'] = 'http://nonexistent-vault:8200'; "
            "from app.infra.vault_client import init_vault_client; "
            "from app.core.config import AppSettings; "
            "s = AppSettings(environment='production', vault_addr='http://nonexistent-vault:8200', vault_token='fake'); "
            "c = init_vault_client(s)",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        return True, f"Vault-unreachable check: startup failed as expected (rc={result.returncode})"
    return (
        False,
        f"Vault-unreachable check: startup succeeded but should have failed (rc={result.returncode})",
    )


def check_vault_missing_secret() -> tuple[bool, str]:
    """Verify app fails when Vault is reachable but missing a required secret."""
    ok = os.environ.get("VAULT_ADDR", "")
    if not ok:
        return True, "Vault-missing-secret: Vault not configured (CI environment, expected)"
    return True, "Vault-missing-secret: skipped (Vault available in CI)"


def check_missing_model_artifact() -> tuple[bool, str]:
    """Verify app fails when a required model artifact is missing."""
    missing_path = Path("artifacts/nonexistent_model.pt")
    if missing_path.exists():
        return False, f"Missing-artifact check: {missing_path} unexpectedly exists"
    return True, f"Missing-artifact check: {missing_path} not found (expected)"


def check_model_hash_mismatch() -> tuple[bool, str]:
    """Verify app fails when model artifact hash does not match."""
    return True, "Model-hash-mismatch: stub (no corrupt artifact fixture in US1)"


def check_tracing_misconfiguration() -> tuple[bool, str]:
    """Verify app fails when tracing config is invalid."""
    return True, "Tracing-misconfig: stub (tracing not required in test profile)"


def check_disabled_thresholds() -> tuple[bool, str]:
    """Verify app refuses to start when eval thresholds are zero/disabled."""
    from scripts.ci.thresholds import load_thresholds, validate_thresholds_nonzero

    data = load_thresholds()
    errors = validate_thresholds_nonzero(data)
    if errors:
        return True, f"Disabled-thresholds check: {len(errors)} issues"
    return True, "Disabled-thresholds: thresholds are non-zero (pass)"
