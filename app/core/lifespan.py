"""FastAPI lifespan management."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
import structlog

from app.core.config import AppSettings
from app.core.logging import configure_logging
from app.infra.database import create_engine, create_session_factory
from app.infra.minio_client import create_minio_client
from app.infra.redis_client import create_redis_client
from app.infra.vault_client import fetch_secrets, init_vault_client


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

    # Create infrastructure clients
    db_engine = create_engine(settings.database_url)
    redis_client = await create_redis_client(settings.redis_url)
    minio_client = create_minio_client(
        settings.minio_endpoint,
        settings.minio_access_key,
        settings.minio_secret_key,
    )

    # Store clients in app state
    app.state.db_engine = db_engine
    app.state.redis = redis_client
    app.state.minio = minio_client
    app.state.vault_client = vault_client
    app.state.settings = settings

    log.info("startup complete")

    yield

    # Shutdown
    await redis_client.close()
    await db_engine.dispose()
    log.info("shutdown complete")
