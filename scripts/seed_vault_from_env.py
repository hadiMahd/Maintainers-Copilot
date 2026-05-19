"""Seed Vault with secrets from .env using Python hvac library.

This is an alternative to scripts/seed_vault_from_env.sh when the vault CLI
is not installed locally. It reads the same .env file and writes to the same
Vault paths.
"""

from __future__ import annotations

import os
from pathlib import Path

import hvac


def load_env_file(path: str) -> dict[str, str]:
    """Parse a .env file into a dict."""
    env_vars: dict[str, str] = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key] = value.strip('"').strip("'")
    return env_vars


def seed_vault(env_path: str = ".env") -> None:
    """Seed Vault dev mode with secrets from .env."""
    env_vars = load_env_file(env_path)

    vault_addr = env_vars.get("VAULT_ADDR", "http://localhost:8200")
    vault_token = env_vars.get("VAULT_TOKEN", "myroot")

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
    app_secret = client.secrets.kv.v2.read_secret_version(path="maintainer-copilot/app")
    azure_secret = client.secrets.kv.v2.read_secret_version(path="maintainer-copilot/azure-openai")
    print(f"\nVerified app secrets: {list(app_secret['data']['data'].keys())}")
    print(f"Verified azure-openai secrets: {list(azure_secret['data']['data'].keys())}")
    print("\nVault seeded successfully from .env")


if __name__ == "__main__":
    seed_vault()