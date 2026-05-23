"""Tests for application configuration."""

import pytest
from pydantic import ValidationError

from app.core.config import AppSettings


def test_valid_settings_construction(monkeypatch):
    """Construct AppSettings with all required fields."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("VAULT_ADDR", "http://localhost:8200")
    monkeypatch.setenv("VAULT_TOKEN", "token")
    settings = AppSettings(_env_file=None)
    assert settings.environment == "test"
    assert settings.vault_addr == "http://localhost:8200"


def test_missing_vault_addr_raises(monkeypatch):
    """Omit VAULT_ADDR and assert ValidationError is raised."""
    monkeypatch.delenv("VAULT_ADDR", raising=False)
    monkeypatch.setenv("VAULT_TOKEN", "token")
    with pytest.raises(ValidationError):
        AppSettings(_env_file=None)


def test_missing_vault_token_raises(monkeypatch):
    """Omit VAULT_TOKEN and assert ValidationError is raised."""
    monkeypatch.delenv("VAULT_TOKEN", raising=False)
    monkeypatch.setenv("VAULT_ADDR", "http://localhost:8200")
    with pytest.raises(ValidationError):
        AppSettings(_env_file=None)


def test_missing_environment_uses_default(monkeypatch):
    """Omit ENVIRONMENT and assert the default is used."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("VAULT_ADDR", "http://localhost:8200")
    monkeypatch.setenv("VAULT_TOKEN", "token")
    settings = AppSettings(_env_file=None)
    assert settings.environment == "local"


def test_vault_resolved_fields_default_none(monkeypatch):
    """Construct valid AppSettings and assert vault-resolved fields are None."""
    monkeypatch.setenv("VAULT_ADDR", "http://localhost:8200")
    monkeypatch.setenv("VAULT_TOKEN", "token")
    settings = AppSettings(_env_file=None)
    assert settings.database_url is None
    assert settings.redis_url is None
    assert settings.minio_endpoint is None
    assert settings.minio_access_key is None
    assert settings.minio_secret_key is None


# ── Phase 3: Classifier / MLflow / Vault-Resolved Settings ──


def test_classifier_settings_defaults(monkeypatch):
    """Classifier artifact and eval settings have sensible defaults."""
    monkeypatch.setenv("VAULT_ADDR", "http://localhost:8200")
    monkeypatch.setenv("VAULT_TOKEN", "token")
    settings = AppSettings(_env_file=None)
    assert settings.classifier_artifact_dir == "artifacts/classifiers"
    assert settings.classifier_golden_set_path == "evals/classification_golden_set.jsonl"
    assert settings.eval_output_dir == "evals"


def test_mlflow_settings_defaults(monkeypatch):
    """MLflow tracking settings have sensible defaults."""
    monkeypatch.setenv("VAULT_ADDR", "http://localhost:8200")
    monkeypatch.setenv("VAULT_TOKEN", "token")
    settings = AppSettings(_env_file=None)
    assert settings.mlflow_tracking_uri == "http://localhost:5000"
    assert settings.mlflow_artifact_root == "mlruns"


def test_vault_resolved_llm_fields_default_none(monkeypatch):
    """Azure OpenAI and LangSmith fields default to None until Vault resolves them."""
    monkeypatch.setenv("VAULT_ADDR", "http://localhost:8200")
    monkeypatch.setenv("VAULT_TOKEN", "token")
    for key in (
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_MODEL",
        "AZURE_OPENAI_EMBEDDING_MODEL",
        "LANGCHAIN_API_KEY",
        "LANGCHAIN_ENDPOINT",
        "LANGCHAIN_PROJECT",
        "LANGSMITH_ENDPOINT",
        "LANGSMITH_PROJECT",
        "SUMMARIZATION_TIMEOUT_SECONDS",
        "LANGSMITH_TRACING_V2",
    ):
        monkeypatch.delenv(key, raising=False)
    settings = AppSettings(_env_file=None)
    assert settings.azure_openai_endpoint is None
    assert settings.azure_openai_api_key is None
    assert settings.azure_openai_model is None
    assert settings.azure_openai_embedding_model is None
    assert settings.langchain_api_key is None


def test_phase7_chat_settings_defaults_and_override(monkeypatch):
    """Phase 7 chat settings expose safe defaults and env overrides."""
    monkeypatch.setenv("VAULT_ADDR", "http://localhost:8200")
    monkeypatch.setenv("VAULT_TOKEN", "token")
    monkeypatch.setenv("CHAT_MAX_TOOL_CALLS", "7")
    monkeypatch.setenv("CHAT_TOTAL_TIMEOUT_SECONDS", "75")
    monkeypatch.setenv("CHAT_PER_TOOL_TIMEOUT_SECONDS", "9")
    monkeypatch.setenv("CHAT_REQUEST_SIZE_LIMIT_BYTES", "9000")
    monkeypatch.setenv("CHAT_CONTEXT_SIZE_LIMIT_CHARS", "15000")
    monkeypatch.setenv("CHAT_RECURSION_LIMIT", "10")
    monkeypatch.setenv("CHAT_PROMPT_SYSTEM_PATH", "prompts/chatbot_system.md")
    monkeypatch.setenv("CHAT_PROMPT_TOOL_POLICY_PATH", "prompts/chatbot_tool_policy.md")
    monkeypatch.setenv("CHAT_PROMPT_UNTRUSTED_CONTEXT_PATH", "prompts/chatbot_untrusted_context.md")
    monkeypatch.setenv("CHAT_TRACING_BACKEND", "langsmith")
    settings = AppSettings(_env_file=None)
    assert settings.chat_max_tool_calls == 7
    assert settings.chat_total_timeout_seconds == 75
    assert settings.chat_per_tool_timeout_seconds == 9
    assert settings.chat_request_size_limit_bytes == 9000
    assert settings.chat_context_size_limit_chars == 15000
    assert settings.chat_recursion_limit == 10
    assert settings.chat_prompt_system_path.endswith("chatbot_system.md")
    assert settings.chat_prompt_tool_policy_path.endswith("chatbot_tool_policy.md")
    assert settings.chat_prompt_untrusted_context_path.endswith("chatbot_untrusted_context.md")
    assert settings.chat_tracing_backend == "langsmith"
