"""Pytest configuration and shared fixtures."""

import pytest
from unittest.mock import MagicMock

from app.core.config import AppSettings
from app.domain.models import ReadinessCheck

# Import health routes to trigger router registration on the global app
import app.api.routes.health  # noqa: F401


@pytest.fixture
def settings(monkeypatch):
    """Return test AppSettings."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("VAULT_ADDR", "http://fake-vault:8200")
    monkeypatch.setenv("VAULT_ROLE_ID", "fake-role")
    monkeypatch.setenv("VAULT_SECRET_ID", "fake-secret")
    return AppSettings(
        environment="test",
        vault_addr="http://fake-vault:8200",
        vault_role_id="fake-role",
        vault_secret_id="fake-secret",
        database_url="postgresql+asyncpg://fake/fake",
        redis_url="redis://fake:6379/0",
        minio_endpoint="fake-minio:9000",
        minio_access_key="fake",
        minio_secret_key="fake",
    )


@pytest.fixture
def mock_vault_client():
    """Return a mock Vault client."""
    client = MagicMock()
    client.is_authenticated.return_value = True
    return client


@pytest.fixture
def mock_vault(monkeypatch, mock_vault_client):
    """Mock Vault client initialization and secret fetching."""

    def mock_init(settings):
        return mock_vault_client

    def mock_fetch(client, mount, path):
        return {
            "database_url": "postgresql+asyncpg://fake/fake",
            "redis_url": "redis://fake:6379/0",
            "minio_endpoint": "fake-minio:9000",
            "minio_access_key": "fake",
            "minio_secret_key": "fake",
        }

    monkeypatch.setattr("app.infra.vault_client.init_vault_client", mock_init)
    monkeypatch.setattr("app.infra.vault_client.fetch_secrets", mock_fetch)


@pytest.fixture
def mock_db(monkeypatch):
    """Mock database probe."""
    async def mock_probe(*args, **kwargs):
        return ReadinessCheck(name="postgres", status="ok")
    monkeypatch.setattr("app.infra.database.probe_database", mock_probe)
    monkeypatch.setattr("app.services.health_service.probe_database", mock_probe)


@pytest.fixture
def mock_redis(monkeypatch):
    """Mock Redis probe."""
    async def mock_probe(*args, **kwargs):
        return ReadinessCheck(name="redis", status="ok")
    monkeypatch.setattr("app.infra.redis_client.probe_redis", mock_probe)
    monkeypatch.setattr("app.services.health_service.probe_redis", mock_probe)


@pytest.fixture
def mock_minio(monkeypatch):
    """Mock MinIO probe."""
    async def mock_probe(*args, **kwargs):
        return ReadinessCheck(name="minio", status="ok")
    monkeypatch.setattr("app.infra.minio_client.probe_minio", mock_probe)
    monkeypatch.setattr("app.services.health_service.probe_minio", mock_probe)


@pytest.fixture
def mock_pgvector(monkeypatch):
    """Mock pgvector probe."""
    async def mock_probe(*args, **kwargs):
        return ReadinessCheck(name="pgvector", status="ok")
    monkeypatch.setattr("app.services.health_service.probe_pgvector", mock_probe)


@pytest.fixture
async def app(settings, mock_vault, mock_db, mock_redis, mock_minio, mock_vault_client):
    """Return an httpx.AsyncClient for the test app."""
    from contextlib import AsyncExitStack, asynccontextmanager
    import httpx
    from app.core.application import app as fastapi_app

    @asynccontextmanager
    async def test_lifespan(app):
        app.state.settings = settings
        app.state.db_engine = None
        app.state.redis = None
        app.state.minio = None
        app.state.vault_client = mock_vault_client
        yield

    fastapi_app.router.lifespan_context = test_lifespan

    async with AsyncExitStack() as stack:
        await stack.enter_async_context(test_lifespan(fastapi_app))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=fastapi_app), base_url="http://test"
        ) as client:
            yield client
