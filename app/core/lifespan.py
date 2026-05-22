"""FastAPI lifespan management."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from pydantic import SecretStr

import app.infra.database as db_mod
from app.core.config import AppSettings
from app.core.logging import configure_logging
from app.domain.errors import ConfigError
from app.infra.conversation_state_adapter import ConversationStateAdapter
from app.infra.database import create_engine, create_session_factory
from app.infra.llm_adapter import AzureChatLLMAdapter, FakeLLMAdapter
from app.infra.minio_client import create_minio_client
from app.infra.model_server_tools import HTTPModelServerTools
from app.infra.prompt_registry import PromptRegistry
from app.infra.rag_generation_client import resolve_generation_client
from app.infra.rag_tool_client import FakeRAGToolClient, RAGToolClient
from app.infra.redis_client import create_redis_client
from app.infra.tracing import FakeTraceAdapter, LangSmithTraceAdapter
from app.infra.vault_client import (
    fetch_secrets,
    init_vault_client,
    resolve_classifier_secrets,
    resolve_jwt_key,
)


def _apply_optional_provider_settings(settings: AppSettings, resolved: dict) -> None:
    """Apply optional Vault-resolved provider settings to the live AppSettings."""
    settings.azure_openai_endpoint = resolved.get("azure_openai_endpoint")
    azure_api_key = resolved.get("azure_openai_api_key")
    settings.azure_openai_api_key = SecretStr(str(azure_api_key)) if azure_api_key else None
    settings.azure_openai_model = resolved.get("azure_openai_model")
    settings.azure_openai_embedding_model = resolved.get("azure_openai_embedding_model")
    settings.rag_azure_generation_endpoint = settings.azure_openai_endpoint
    settings.rag_azure_generation_api_key = str(azure_api_key) if azure_api_key else None
    settings.rag_azure_generation_model = settings.azure_openai_model
    settings.rag_azure_embedding_endpoint = settings.azure_openai_endpoint
    settings.rag_azure_embedding_api_key = str(azure_api_key) if azure_api_key else None
    if settings.rag_azure_embedding_endpoint and settings.rag_azure_embedding_api_key:
        settings.rag_embedding_model = (
            settings.azure_openai_embedding_model or "text-embedding-3-small"
        )
        settings.rag_embedding_dim = 1536
    langchain_api_key = resolved.get("langchain_api_key")
    settings.langchain_api_key = SecretStr(str(langchain_api_key)) if langchain_api_key else None
    settings.langsmith_endpoint = resolved.get("langchain_endpoint")
    settings.langsmith_project = resolved.get("langchain_project")


def _build_rag_tool_client(db_session_factory, settings: AppSettings) -> RAGToolClient:
    generation_client = resolve_generation_client(settings)
    return RAGToolClient(
        session_factory=db_session_factory,
        generation_client=generation_client,
        settings=settings,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    """Manage application lifespan: startup and shutdown."""
    settings = AppSettings()
    configure_logging(settings)
    log = structlog.get_logger()

    # Initialize Vault client
    vault_client = init_vault_client(settings)

    # Fetch secrets from Vault
    secrets = fetch_secrets(
        vault_client,
        settings.vault_secret_mount,
        settings.vault_secret_path,
    )
    settings.database_url = secrets.get("database_url")
    settings.redis_url = secrets.get("redis_url")
    settings.minio_endpoint = secrets.get("minio_endpoint")
    settings.minio_access_key = secrets.get("minio_access_key")
    settings.minio_secret_key = secrets.get("minio_secret_key")
    _apply_optional_provider_settings(
        settings,
        resolve_classifier_secrets(vault_client, settings),
    )

    # Resolve JWT signing keys from Vault
    try:
        jwt_keys = resolve_jwt_key(vault_client, settings)
        settings.jwt_private_key = jwt_keys["private_key"]
        settings.jwt_public_key = jwt_keys["public_key"]
    except ConfigError:
        if settings.environment != "test":
            raise

    # Create infrastructure clients
    db_engine = create_engine(settings.database_url)
    db_session_factory = create_session_factory(db_engine)
    db_mod.async_session_factory = db_session_factory
    redis_client = await create_redis_client(settings.redis_url)
    minio_client = create_minio_client(
        settings.minio_endpoint,
        settings.minio_access_key,
        settings.minio_secret_key,
    )

    # Store clients in app state
    app.state.db_engine = db_engine
    app.state.db_session_factory = db_session_factory
    app.state.redis = redis_client
    app.state.minio = minio_client
    app.state.vault_client = vault_client
    app.state.settings = settings
    app.state.prompt_registry = PromptRegistry.from_settings(settings)
    app.state.chat_conversation_state_adapter = ConversationStateAdapter(redis_client)
    app.state.chat_model_server_tools = HTTPModelServerTools(
        base_url=settings.chat_model_server_base_url,
    )
    app.state.chat_rag_tool_client = (
        FakeRAGToolClient()
        if settings.environment == "test"
        else _build_rag_tool_client(db_session_factory, settings)
    )
    app.state.chat_trace_adapter = (
        LangSmithTraceAdapter.from_settings(settings)
        if settings.chat_tracing_backend == "langsmith"
        else FakeTraceAdapter()
    )
    app.state.chat_llm_adapter = (
        AzureChatLLMAdapter(settings) if settings.environment != "test" else FakeLLMAdapter()
    )

    log.info("startup complete")

    yield

    # Shutdown
    await redis_client.close()
    await db_engine.dispose()
    log.info("shutdown complete")
