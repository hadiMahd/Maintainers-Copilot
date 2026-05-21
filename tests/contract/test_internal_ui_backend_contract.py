"""Contract tests for Phase 8 internal UI backend endpoints.

Verifies response shapes match the OpenAPI contract in
contracts/internal-ui-backend.openapi.yaml.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.domain.auth import AuthContext
from app.domain.errors import WidgetConfigNotFoundError
from app.domain.memory_inspector import MemoryInspectionResult, MemoryRecordRead
from app.domain.widget_config import EmbedSnippetRead, WidgetConfigRead


@pytest.fixture
def test_key_pair():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return {"private_key": private_pem, "public_key": public_pem}


@pytest.fixture
def mock_session_factory():
    @asynccontextmanager
    async def factory():
        yield AsyncMock()

    return factory


def _patch_app_state(app, test_key_pair, mock_session_factory):
    settings = MagicMock()
    settings.jwt_private_key = test_key_pair["private_key"]
    settings.jwt_public_key = test_key_pair["public_key"]
    settings.jwt_algorithm = "RS256"
    settings.jwt_access_token_expire_minutes = 30
    settings.jwt_refresh_token_expire_days = 7
    settings.environment = "test"
    app.state.settings = settings

    import app.infra.database as db_mod
    db_mod.async_session_factory = mock_session_factory


@pytest.fixture
async def client(test_key_pair, mock_session_factory, monkeypatch):
    """Create app, patch state, return async client."""
    monkeypatch.delenv("VAULT_ADDR", raising=False)
    monkeypatch.delenv("VAULT_TOKEN", raising=False)
    monkeypatch.setenv("VAULT_ADDR", "http://fake-vault:8200")
    monkeypatch.setenv("VAULT_TOKEN", "fake-token")

    from app.core.application import create_app

    app = create_app()
    _patch_app_state(app, test_key_pair, mock_session_factory)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestWidgetConfigList:
    async def test_unauthenticated_returns_401(self, client):
        resp = await client.get("/admin/widget-configs/")
        assert resp.status_code == 401

    async def test_list_returns_items_array(self, client, monkeypatch):
        app = client._transport.app
        from app.api.dependencies.authorization import require_admin
        from app.api.dependencies.auth import get_current_user

        admin_ctx = AuthContext(user_id="admin-1", email="a@t.com", role="admin")

        async def mock_admin():
            return admin_ctx

        app.dependency_overrides[require_admin] = mock_admin
        app.dependency_overrides[get_current_user] = mock_admin

        mock_svc = AsyncMock()
        mock_svc.list_configs = AsyncMock(
            return_value=[
                WidgetConfigRead(
                    id="cfg-1", name="Test Widget",
                    allowed_origins=["https://example.com"], theme="default",
                    is_enabled=True,
                    widget_id="wid-1", position="bottom-right", enabled_tools=[],
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            ]
        )

        import app.api.routes.widget_configs as wc_mod
        monkeypatch.setattr(wc_mod, "_get_widget_config_service", lambda r: mock_svc)

        resp = await client.get("/admin/widget-configs/")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == "cfg-1"


class TestWidgetConfigCreate:
    async def test_create_returns_201(self, client, monkeypatch):
        app = client._transport.app
        from app.api.dependencies.authorization import require_admin
        from app.api.dependencies.auth import get_current_user

        admin_ctx = AuthContext(user_id="admin-1", email="a@t.com", role="admin")

        async def mock_admin():
            return admin_ctx

        app.dependency_overrides[require_admin] = mock_admin
        app.dependency_overrides[get_current_user] = mock_admin

        mock_svc = AsyncMock()
        mock_svc.create_config = AsyncMock(
            return_value=WidgetConfigRead(
                id="cfg-new", name="New Widget",
                allowed_origins=["http://localhost"], theme="dark",
                welcome_message="Hello", is_enabled=True,
                    widget_id="wid-1", position="bottom-right", enabled_tools=[],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )

        import app.api.routes.widget_configs as wc_mod
        monkeypatch.setattr(wc_mod, "_get_widget_config_service", lambda r: mock_svc)

        resp = await client.post(
            "/admin/widget-configs/",
            json={"name": "New Widget", "allowed_origins": ["http://localhost"], "theme": "dark"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == "cfg-new"
        assert data["name"] == "New Widget"


class TestEmbedSnippet:
    async def test_embed_snippet_response_shape(self, client, monkeypatch):
        app = client._transport.app
        from app.api.dependencies.authorization import require_admin
        from app.api.dependencies.auth import get_current_user

        async def mock_admin():
            return AuthContext(user_id="admin-1", email="a@t.com", role="admin")

        app.dependency_overrides[require_admin] = mock_admin
        app.dependency_overrides[get_current_user] = mock_admin

        mock_svc = AsyncMock()
        mock_svc.generate_embed_snippet = AsyncMock(
            return_value=EmbedSnippetRead(
                widget_config_id="cfg-1",
                snippet='<script data-mc-widget-config="cfg-1"></script>\n<script src="BASE_URL/widget/loader.js"></script>',
                generated_at=datetime.now(timezone.utc),
            )
        )

        import app.api.routes.widget_configs as wc_mod
        monkeypatch.setattr(wc_mod, "_get_widget_config_service", lambda r: mock_svc)

        resp = await client.get("/admin/widget-configs/cfg-1/embed-snippet")
        assert resp.status_code == 200
        data = resp.json()
        assert data["widget_config_id"] == "cfg-1"
        assert "loader.js" in data["snippet"]

    async def test_embed_snippet_not_found_returns_404(self, client, monkeypatch):
        app = client._transport.app
        from app.api.dependencies.authorization import require_admin
        from app.api.dependencies.auth import get_current_user

        async def mock_admin():
            return AuthContext(user_id="admin-1", email="a@t.com", role="admin")

        app.dependency_overrides[require_admin] = mock_admin
        app.dependency_overrides[get_current_user] = mock_admin

        mock_svc = AsyncMock()
        mock_svc.generate_embed_snippet = AsyncMock(
            side_effect=WidgetConfigNotFoundError("not found")
        )

        import app.api.routes.widget_configs as wc_mod
        monkeypatch.setattr(wc_mod, "_get_widget_config_service", lambda r: mock_svc)

        resp = await client.get("/admin/widget-configs/nonexistent/embed-snippet")
        assert resp.status_code == 404


class TestMemoryInspection:
    async def test_unauthenticated_returns_401(self, client):
        resp = await client.get("/memory/long-term")
        assert resp.status_code == 401

    async def test_returns_200_with_items_scope_own(self, client, monkeypatch):
        app = client._transport.app
        from app.api.dependencies.auth import get_current_user

        async def mock_user():
            return AuthContext(user_id="u1", email="u@t.com", role="user")

        app.dependency_overrides[get_current_user] = mock_user

        mock_svc = AsyncMock()
        mock_svc.inspect_memory = AsyncMock(
            return_value=MemoryInspectionResult(
                items=[
                    MemoryRecordRead(
                        id="mem-1", owner_user_id="u1", memory_type="semantic",
                        redacted_content="[REDACTED]", source="chat",
                        created_at=datetime.now(timezone.utc),
                    )
                ],
                scope="own",
            )
        )

        import app.api.routes.memory_inspector as mi_mod
        monkeypatch.setattr(mi_mod, "_get_memory_inspector_service", lambda r: mock_svc)

        resp = await client.get("/memory/long-term?limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["scope"] == "own"
        assert len(data["items"]) == 1

    async def test_admin_scope_returns_admin(self, client, monkeypatch):
        app = client._transport.app
        from app.api.dependencies.auth import get_current_user

        async def mock_admin():
            return AuthContext(user_id="admin-1", email="admin@t.com", role="admin")

        app.dependency_overrides[get_current_user] = mock_admin

        mock_svc = AsyncMock()
        mock_svc.inspect_memory = AsyncMock(
            return_value=MemoryInspectionResult(items=[], scope="admin")
        )

        import app.api.routes.memory_inspector as mi_mod
        monkeypatch.setattr(mi_mod, "_get_memory_inspector_service", lambda r: mock_svc)

        resp = await client.get("/memory/long-term?limit=5")
        assert resp.status_code == 200
        assert resp.json()["scope"] == "admin"
