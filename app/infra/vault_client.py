"""Vault AppRole client."""

import hvac

from app.core.config import AppSettings
from app.domain.errors import ConfigError


def init_vault_client(settings: AppSettings) -> hvac.Client:
    """Initialize and authenticate a Vault client using AppRole.

    Raises ConfigError if authentication fails.
    """
    client = hvac.Client(url=settings.vault_addr)
    try:
        client.auth.approle.login(
            role_id=settings.vault_role_id,
            secret_id=settings.vault_secret_id,
        )
    except Exception as exc:
        raise ConfigError(
            "Vault AppRole authentication failed",
            details={"vault_addr": settings.vault_addr},
        ) from exc

    if not client.is_authenticated():
        raise ConfigError(
            "Vault AppRole authentication failed",
            details={"vault_addr": settings.vault_addr},
        )

    return client


def fetch_secrets(client: hvac.Client, mount: str, path: str) -> dict:
    """Read a KV-v2 secret from Vault.

    Raises ConfigError if the path is missing or required keys are absent.
    """
    try:
        response = client.secrets.kv.v2.read_secret_version(
            path=path,
            mount_point=mount,
        )
    except Exception as exc:
        raise ConfigError(
            f"Vault secret not found at {mount}/{path}",
            details={"mount": mount, "path": path},
        ) from exc

    data = response.get("data", {}).get("data", {})
    if not data:
        raise ConfigError(
            f"Vault secret empty at {mount}/{path}",
            details={"mount": mount, "path": path},
        )

    return data
