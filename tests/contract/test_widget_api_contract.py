"""Contract tests for admin widget CRUD endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI

from app.api.routes.widget_configs import router as widget_configs_router
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.authorization import require_admin
from app.domain.auth import AuthContext


def _make_read_dict(id="cfg-1", name="Test", widget_id="wid-1", theme="dark"):
    return {
        "id": id,
        "widget_id": widget_id,
        "name": name,
        "allowed_origins": ["https://example.com"],
        "theme": theme,
        "greeting": "Hi",
        "welcome_message": "Hello",
        "position": "bottom-right",
        "enabled_tools": ["classify_issue"],
        "is_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def mock_widget_service():
    svc = MagicMock()
    svc.list_configs = AsyncMock(return_value=[])
    svc.create_config = AsyncMock(return_value=MagicMock(
        model_dump=lambda mode=None: _make_read_dict(),
    ))
    svc.get_config = AsyncMock(side_effect=lambda config_id, request_id=None: MagicMock(
        model_dump=lambda mode=None: _make_read_dict(id=config_id),
    ))
    svc.update_config = AsyncMock(side_effect=lambda config_id, data, updated_by_user_id, audit_service, request_id=None: MagicMock(
        model_dump=lambda mode=None: _make_read_dict(id=config_id, theme=data.theme if hasattr(data, 'theme') else "dark"),
    ))
    svc.delete_config = AsyncMock(return_value=MagicMock(
        id="cfg-1",
        widget_id="wid-1",
        name="Test",
        model_dump=lambda mode=None: _make_read_dict(),
    ))
    svc.generate_embed_snippet = AsyncMock(return_value=MagicMock(
        model_dump=lambda mode=None: {
            "widget_config_id": "cfg-1",
            "snippet": '<!-- Maintainer Copilot Widget (id: wid-1) -->\n<script src="BASE_URL/widget/loader.js" data-widget-id="wid-1"></script>',
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    ))
    return svc


@pytest.fixture
def mock_audit_service():
    svc = MagicMock()
    svc.log_action = AsyncMock()
    return svc


def _build_app(mock_svc, mock_audit, user_role="admin"):
    import app.api.routes.widget_configs as wc_routes
    wc_routes._get_widget_config_service = lambda request: mock_svc
    wc_routes._get_audit_service = lambda request: mock_audit

    from app.api.error_handlers import register_error_handlers

    app = FastAPI()

    async def _fake_user():
        return AuthContext(user_id="test-user", email="test@test.com", role=user_role)

    app.dependency_overrides[get_current_user] = _fake_user
    app.include_router(widget_configs_router, prefix="/admin/widget-configs")
    register_error_handlers(app)
    return app


@pytest.mark.asyncio
async def test_list_configs_returns_items(mock_widget_service, mock_audit_service):
    mock_widget_service.list_configs.return_value = [
        MagicMock(model_dump=lambda mode=None: _make_read_dict(id="cfg-1", name="Test", widget_id="wid-1")),
    ]

    app = _build_app(mock_widget_service, mock_audit_service, user_role="admin")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/admin/widget-configs/")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data


@pytest.mark.asyncio
async def test_create_config_returns_201(mock_widget_service, mock_audit_service):
    app = _build_app(mock_widget_service, mock_audit_service, user_role="admin")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/admin/widget-configs/",
            json={"name": "Test", "allowed_origins": ["https://example.com"]},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == "cfg-1"
        assert data["widget_id"] == "wid-1"


@pytest.mark.asyncio
async def test_update_config_returns_updated_theme(mock_widget_service, mock_audit_service):
    from app.domain.widget_config import WidgetConfigUpdate

    async def _mock_update(config_id, data, updated_by_user_id, audit_service, request_id=None):
        theme = "dark"
        if isinstance(data, WidgetConfigUpdate) and data.theme:
            theme = data.theme
        return MagicMock(model_dump=lambda mode=None: _make_read_dict(id=config_id, theme=theme))

    mock_widget_service.update_config = AsyncMock(side_effect=_mock_update)

    app = _build_app(mock_widget_service, mock_audit_service, user_role="admin")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.patch(
            "/admin/widget-configs/cfg-1",
            json={"theme": "light"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["theme"] == "light"


@pytest.mark.asyncio
async def test_delete_config_returns_config_id_and_widget_id(mock_widget_service, mock_audit_service):
    app = _build_app(mock_widget_service, mock_audit_service, user_role="admin")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.delete("/admin/widget-configs/cfg-1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "cfg-1"
        assert data["widget_id"] == "wid-1"
        assert "deleted_at" in data


@pytest.mark.asyncio
async def test_embed_snippet_uses_widget_id(mock_widget_service, mock_audit_service):
    app = _build_app(mock_widget_service, mock_audit_service, user_role="admin")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/admin/widget-configs/cfg-1/embed-snippet")
        assert resp.status_code == 200
        data = resp.json()
        assert "data-widget-id=" in data["snippet"]
        assert "wid-1" in data["snippet"]
        assert "loader.js" in data["snippet"]


@pytest.mark.asyncio
async def test_non_admin_cannot_create_config(mock_widget_service, mock_audit_service):
    app = _build_app(mock_widget_service, mock_audit_service, user_role="user")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/admin/widget-configs/",
            json={"name": "Test", "allowed_origins": ["https://example.com"]},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_non_admin_cannot_update_config(mock_widget_service, mock_audit_service):
    app = _build_app(mock_widget_service, mock_audit_service, user_role="user")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.patch(
            "/admin/widget-configs/cfg-1",
            json={"theme": "light"},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_non_admin_cannot_delete_config(mock_widget_service, mock_audit_service):
    app = _build_app(mock_widget_service, mock_audit_service, user_role="user")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.delete("/admin/widget-configs/cfg-1")
        assert resp.status_code == 403
