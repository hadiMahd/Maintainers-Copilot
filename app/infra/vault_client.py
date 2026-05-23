"""Vault bootstrap client."""

from __future__ import annotations

import hvac

from app.core.config import AppSettings
from app.domain.errors import ConfigError


def init_vault_client(settings: AppSettings) -> hvac.Client:
    """Initialize and authenticate a Vault client using a bootstrap token.

    Raises ConfigError if authentication fails.
    """
    client = hvac.Client(
        url=settings.vault_addr,
        token=settings.vault_token.get_secret_value(),
    )
    try:
        authenticated = client.is_authenticated()
    except Exception as exc:
        raise ConfigError(
            "Vault token authentication failed",
            details={"vault_addr": settings.vault_addr},
        ) from exc

    if not authenticated:
        raise ConfigError(
            "Vault token authentication failed",
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


def resolve_classifier_secrets(client: hvac.Client, settings: AppSettings) -> dict:
    """Resolve Phase 3 classifier secrets from Vault.

    Returns a dict with Azure OpenAI and LangSmith keys when present.
    Never raises for missing optional secrets; returns empty values instead.
    """
    result: dict = {}

    try:
        azure_secrets = fetch_secrets(
            client, settings.vault_secret_mount, "maintainer-copilot/azure-openai"
        )
        result["azure_openai_endpoint"] = azure_secrets.get("endpoint")
        result["azure_openai_api_key"] = azure_secrets.get("api_key")
        result["azure_openai_model"] = azure_secrets.get("openai_model")
        result["azure_openai_embedding_model"] = azure_secrets.get("embedding_model")
    except ConfigError:
        result.setdefault("azure_openai_endpoint", None)
        result.setdefault("azure_openai_api_key", None)
        result.setdefault("azure_openai_model", None)
        result.setdefault("azure_openai_embedding_model", None)

    try:
        langsmith_secrets = fetch_secrets(
            client, settings.vault_secret_mount, "maintainer-copilot/langsmith"
        )
        result["langchain_api_key"] = langsmith_secrets.get("api_key")
        result["langchain_endpoint"] = langsmith_secrets.get("endpoint")
        result["langchain_project"] = langsmith_secrets.get("project")
        result["langchain_tracing"] = langsmith_secrets.get("tracing")
    except ConfigError:
        result.setdefault("langchain_api_key", None)
        result.setdefault("langchain_endpoint", None)
        result.setdefault("langchain_project", None)
        result.setdefault("langchain_tracing", None)

    return result


def resolve_jwt_key(client: hvac.Client, settings: AppSettings) -> dict:
    """Resolve the RS256 JWT signing key pair from Vault.

    Returns a dict with ``private_key`` and ``public_key`` PEM strings.
    Raises ConfigError if the JWT key path is missing or required fields
    are absent.
    """
    data = fetch_secrets(client, settings.vault_secret_mount, settings.jwt_vault_key_path)
    private_key = data.get("private_key")
    public_key = data.get("public_key")
    if not private_key or not public_key:
        raise ConfigError(
            "JWT signing key incomplete in Vault",
            details={"path": settings.jwt_vault_key_path},
        )
    return {"private_key": private_key, "public_key": public_key}
