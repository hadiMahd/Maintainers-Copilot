"""Startup negative-case checks: Vault, model, tracing, threshold failures.

Performs negative-test assertions to verify the system fails closed when any
required dependency is unavailable or misconfigured.

Checks performed:
  - vault-unreachable: App fails when Vault is unreachable
  - vault-missing-secret: App fails when Vault is reachable but secret missing
  - missing-model-artifact: Required model artifact is absent
  - model-hash-mismatch: Model artifact hash does not match model card
  - tracing-misconfig: Tracing configuration is invalid
  - disabled-thresholds: Eval thresholds are zero or disabled

Each check should return (True, message) when the system correctly fails closed.
A (False, message) means the system succeeded when it should have failed.
"""

import sys

from scripts.ci.common import fail, pass_gate
from scripts.ci.startup_checks import (
    check_disabled_thresholds,
    check_missing_model_artifact,
    check_model_hash_mismatch,
    check_tracing_misconfiguration,
    check_vault_missing_secret,
    check_vault_unreachable,
)


if __name__ == "__main__":
    checks = [
        ("vault-unreachable", check_vault_unreachable),
        ("vault-missing-secret", check_vault_missing_secret),
        ("missing-model-artifact", check_missing_model_artifact),
        ("model-hash-mismatch", check_model_hash_mismatch),
        ("tracing-misconfig", check_tracing_misconfiguration),
        ("disabled-thresholds", check_disabled_thresholds),
    ]

    failures: list[str] = []
    passed: list[str] = []

    for name, fn in checks:
        ok, msg = fn()
        if not ok:
            failures.append(f"{name}: {msg}")
            print(f"  [FAIL] {name}: {msg}")
        else:
            passed.append(name)
            print(f"  [PASS] {name}: {msg}")

    if failures:
        safe = "; ".join(failures[:3])
        if len(failures) > 3:
            safe += f" ... and {len(failures) - 3} more"
        fail(f"Startup failures: {len(failures)} check(s) failed: {safe}")
        sys.exit(1)

    pass_gate(
        f"Startup failures: {len(checks)}/{len(checks)} negative cases passed "
        f"(system correctly fails closed)"
    )
