"""Startup negative-case checks: Vault, model, tracing, threshold failures."""

from scripts.ci.common import fail, pass_gate
from scripts.ci.startup_checks import (
    check_vault_unreachable,
    check_missing_model_artifact,
    check_model_hash_mismatch,
    check_tracing_misconfiguration,
    check_disabled_thresholds,
)


if __name__ == "__main__":
    checks = [
        ("vault-unreachable", check_vault_unreachable),
        ("missing-model-artifact", check_missing_model_artifact),
        ("model-hash-mismatch", check_model_hash_mismatch),
        ("tracing-misconfig", check_tracing_misconfiguration),
        ("disabled-thresholds", check_disabled_thresholds),
    ]
    failures = []
    for name, fn in checks:
        ok, msg = fn()
        if not ok:
            failures.append(f"{name}: {msg}")
        print(f"  {name}: {'PASS' if ok else 'FAIL'} - {msg}")

    if failures:
        fail(f"Startup failures: {len(failures)} check(s) failed: {'; '.join(failures[:3])}")
    pass_gate(f"Startup failures: {len(checks)} negative cases passed (stub - full check in US3)")
