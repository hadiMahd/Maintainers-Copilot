"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application settings resolved from environment variables."""

    # Required fields (no defaults)
    environment: str
    vault_addr: str
    vault_role_id: str
    vault_secret_id: str

    # Optional fields with defaults
    log_level: str = "INFO"
    service_name: str = "maintainer-copilot"
    vault_secret_mount: str = "secret"
    vault_secret_path: str = "maintainer-copilot/app"
    request_id_header: str = "X-Request-ID"

    # Vault-resolved fields (populated by lifespan, not at construction)
    database_url: str | None = None
    redis_url: str | None = None
    minio_endpoint: str | None = None
    minio_access_key: str | None = None
    minio_secret_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )
