"""Seed Vault with secrets from .env using the Python hvac client.

Usage:
    uv run python scripts/seed_vault_from_env.py .env

The script is intended for local/dev bootstrap after Vault has started.
It keeps the runtime contract unchanged: app containers still receive only
``VAULT_ADDR`` and ``VAULT_TOKEN`` and resolve all other secrets from Vault.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

import hvac


REQUIRED_ENV_VARS = (
    "APP_DATABASE_URL",
    "APP_REDIS_URL",
    "APP_MINIO_ENDPOINT",
    "APP_MINIO_ACCESS_KEY",
    "APP_MINIO_SECRET_KEY",
    "JWT_SIGNING_KEY",
    "AZURE_OPENAI_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_MODEL",
    "AZURE_EMBEDDING_MODEL",
    "LANGSMITH_TRACING",
    "LANGSMITH_ENDPOINT",
    "LANGSMITH_API_KEY",
    "LANGSMITH_PROJECT",
)


def load_env_file(path: str) -> dict[str, str]:
    """Parse a .env file into a dict."""
    env_vars: dict[str, str] = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key] = value.strip('"').strip("'")
    return env_vars


def wait_for_vault(vault_addr: str, timeout_seconds: float) -> None:
    """Wait until the Vault health endpoint responds."""
    deadline = time.monotonic() + timeout_seconds
    health_url = vault_addr.rstrip("/") + "/v1/sys/health"

    while True:
        try:
            request = urllib.request.Request(health_url, method="GET")
            with urllib.request.urlopen(request, timeout=3):
                return
        except (urllib.error.URLError, TimeoutError):
            if time.monotonic() >= deadline:
                raise RuntimeError(f"Vault did not become healthy within {timeout_seconds:.0f}s")
            time.sleep(1)


def require_seed_values(env_vars: dict[str, str]) -> None:
    """Fail fast if a required bootstrap value is missing."""
    missing = [name for name in REQUIRED_ENV_VARS if not env_vars.get(name)]
    if missing:
        names = ", ".join(sorted(missing))
        raise RuntimeError(f"Missing required seed values in env/bootstrap input: {names}")


def seed_vault(env_path: str = ".env", *, timeout_seconds: float = 30.0) -> None:
    """Seed Vault dev mode with secrets from .env."""
    env_vars = load_env_file(env_path)
    require_seed_values(env_vars)

    vault_addr = os.environ.get("VAULT_ADDR") or env_vars.get("VAULT_ADDR") or "http://localhost:8200"
    vault_token = os.environ.get("VAULT_TOKEN") or env_vars.get("VAULT_TOKEN") or "dev-root-token"

    wait_for_vault(vault_addr, timeout_seconds)

    client = hvac.Client(url=vault_addr, token=vault_token)
    if not client.is_authenticated():
        raise RuntimeError(f"Could not authenticate to Vault at {vault_addr}")

    # Enable KV v2 if not already enabled
    try:
        client.sys.enable_secrets_engine("kv-v2", path="secret")
    except hvac.exceptions.InvalidRequest:
        pass  # Already enabled

    # Seed app secrets
    client.secrets.kv.v2.create_or_update_secret(
        path="maintainer-copilot/app",
        secret={
            "database_url": env_vars.get("APP_DATABASE_URL", ""),
            "redis_url": env_vars.get("APP_REDIS_URL", ""),
            "minio_endpoint": env_vars.get("APP_MINIO_ENDPOINT", ""),
            "minio_access_key": env_vars.get("APP_MINIO_ACCESS_KEY", ""),
            "minio_secret_key": env_vars.get("APP_MINIO_SECRET_KEY", ""),
            "jwt_signing_key": env_vars.get("JWT_SIGNING_KEY", ""),
        },
    )
    print("Seeded secret/maintainer-copilot/app")

    # Seed Azure OpenAI secrets
    client.secrets.kv.v2.create_or_update_secret(
        path="maintainer-copilot/azure-openai",
        secret={
            "endpoint": env_vars.get("AZURE_OPENAI_ENDPOINT", ""),
            "api_key": env_vars.get("AZURE_OPENAI_KEY", ""),
            "openai_model": env_vars.get("AZURE_OPENAI_MODEL", ""),
            "embedding_model": env_vars.get("AZURE_EMBEDDING_MODEL", ""),
        },
    )
    print("Seeded secret/maintainer-copilot/azure-openai")

    # Seed LangSmith secrets
    client.secrets.kv.v2.create_or_update_secret(
        path="maintainer-copilot/langsmith",
        secret={
            "tracing": env_vars.get("LANGSMITH_TRACING", ""),
            "endpoint": env_vars.get("LANGSMITH_ENDPOINT", ""),
            "api_key": env_vars.get("LANGSMITH_API_KEY", ""),
            "project": env_vars.get("LANGSMITH_PROJECT", ""),
        },
    )
    print("Seeded secret/maintainer-copilot/langsmith")

    # Verify
    app_secret = client.secrets.kv.v2.read_secret_version(
        path="maintainer-copilot/app",
        raise_on_deleted_version=True,
    )
    azure_secret = client.secrets.kv.v2.read_secret_version(
        path="maintainer-copilot/azure-openai",
        raise_on_deleted_version=True,
    )
    print(f"\nVerified app secrets: {list(app_secret['data']['data'].keys())}")
    print(f"Verified azure-openai secrets: {list(azure_secret['data']['data'].keys())}")
    print("\nVault seeded successfully from .env")


def parse_args() -> argparse.Namespace:
    """Parse CLI args."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "env_path",
        nargs="?",
        default=".env",
        help="Path to the local bootstrap env file (default: .env).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Seconds to wait for Vault health before failing (default: 30).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    env_path = Path(args.env_path)
    if not env_path.is_file():
        raise SystemExit(f"env file not found: {env_path}")
    seed_vault(str(env_path), timeout_seconds=args.timeout)
