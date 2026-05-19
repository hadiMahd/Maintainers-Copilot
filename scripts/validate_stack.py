#!/usr/bin/env python3
"""Validate local stack prerequisites."""

import subprocess
import sys
import urllib.request


def main() -> None:
    """Run all validation checks."""
    checks = []

    # 1. VAULT_ADDR
    vault_addr = subprocess.os.environ.get("VAULT_ADDR", "").strip()
    if vault_addr:
        checks.append(("VAULT_ADDR set", True))
    else:
        checks.append(("VAULT_ADDR set", False))
        print("ERROR: VAULT_ADDR is not set or empty")
        sys.exit(1)

    # 2. VAULT_TOKEN
    vault_token = subprocess.os.environ.get("VAULT_TOKEN", "").strip()
    if vault_token:
        checks.append(("VAULT_TOKEN set", True))
    else:
        checks.append(("VAULT_TOKEN set", False))
        print("ERROR: VAULT_TOKEN is not set or empty")
        sys.exit(1)

    # 3. docker compose config
    result = subprocess.run(
        ["docker", "compose", "config"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        checks.append(("docker compose config", True))
    else:
        checks.append(("docker compose config", False))
        print(f"ERROR: docker compose config failed:\n{result.stderr}")
        sys.exit(1)

    # 4. Vault health endpoint
    health_url = vault_addr.rstrip("/") + "/v1/sys/health"
    try:
        req = urllib.request.Request(health_url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as response:
            checks.append(("Vault health endpoint", True))
    except Exception as exc:
        checks.append(("Vault health endpoint", False))
        print(f"ERROR: Vault health check failed: {exc}")
        sys.exit(1)

    # Summary
    print("\nValidation Summary:")
    for name, passed in checks:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")

    sys.exit(0)


if __name__ == "__main__":
    main()
