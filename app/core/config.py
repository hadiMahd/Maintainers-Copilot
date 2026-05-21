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

    # Phase 4 — Summarization adapter settings
    summarization_timeout_seconds: int = 15
    summarization_max_input_chars: int = 8_000
    langsmith_endpoint: str | None = None
    langsmith_project: str | None = None

    # Phase 5 — RAG pipeline settings
    rag_embedding_model: str = "all-MiniLM-L6-v2"
    rag_embedding_dim: int = 384
    rag_embedding_candidates: list[str] = ["all-MiniLM-L6-v2", "text-embedding-3-small"]
    rag_hybrid_sparse_weight: float = 0.3
    rag_hybrid_dense_weight: float = 0.7
    rag_reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    rag_reranker_top_k: int = 10
    rag_generation_timeout_seconds: int = 30
    rag_judge_timeout_seconds: int = 15
    rag_snapshot_retention_conversations: int = 50
    rag_eval_hit_at_5_threshold: float = 0.0
    rag_eval_mrr_at_10_threshold: float = 0.0
    rag_azure_embedding_endpoint: str | None = None
    rag_azure_embedding_api_key: str | None = None
    rag_azure_generation_endpoint: str | None = None
    rag_azure_generation_api_key: str | None = None
    rag_azure_generation_model: str | None = None

    # Phase 6 — Auth settings
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    jwt_algorithm: str = "RS256"
    jwt_vault_key_path: str = "maintainer-copilot/jwt"

    # Phase 6 — Admin invitation
    admin_invitation_expire_hours: int = 48

    # Phase 6 — Short-term memory
    short_term_memory_ttl_seconds: int = 1800

    # Phase 6 — Long-term memory
    long_term_memory_type: str = "semantic"

    # Phase 6 — Vault-resolved (populated by lifespan)
    jwt_private_key: str | None = None
    jwt_public_key: str | None = None

    # Phase 7 — Chat backend settings
    chat_max_tool_calls: int = 5
    chat_total_timeout_seconds: int = 60
    chat_per_tool_timeout_seconds: int = 10
    chat_request_size_limit_bytes: int = 8_000
    chat_context_size_limit_chars: int = 12_000
    chat_recursion_limit: int = 8
    chat_prompt_system_path: str = "prompts/chatbot_system.md"
    chat_prompt_tool_policy_path: str = "prompts/chatbot_tool_policy.md"
    chat_prompt_untrusted_context_path: str = "prompts/chatbot_untrusted_context.md"
    chat_tracing_backend: str = "fake"
    chat_model_server_base_url: str = "http://localhost:8001"
    azure_openai_api_version: str = "2024-02-01"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )
