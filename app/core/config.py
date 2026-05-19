"""Application configuration."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application settings resolved from environment variables."""

    # Required Vault bootstrap fields
    vault_addr: str
    vault_token: SecretStr

    # Optional fields with defaults
    environment: str = "local"
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

    # Phase 3 — Classifier artifacts & evaluation
    classifier_artifact_dir: str = "artifacts/classifiers"
    classifier_golden_set_path: str = "evals/classification_golden_set.jsonl"
    eval_output_dir: str = "evals"

    # Phase 3 — MLflow tracking
    mlflow_tracking_uri: str = "http://localhost:5000"
    mlflow_artifact_root: str = "mlruns"

    # Phase 3 — MinIO classifier bucket
    minio_classifier_bucket: str = "maintainer-classifiers"

    # Phase 3 — Azure OpenAI (resolved from Vault at runtime)
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: SecretStr | None = None
    azure_openai_model: str | None = None
    azure_openai_embedding_model: str | None = None

    # Phase 3 — LangSmith tracing (resolved from Vault at runtime)
    langchain_api_key: SecretStr | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )
