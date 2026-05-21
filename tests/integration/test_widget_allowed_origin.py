"""Integration test for allowed-origin embed flow."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI

from app.api.routes.widget_loader import router as widget_loader_router
from app.api.routes.widget_public import router as widget_public_router
from app.api.dependencies.auth import get_current_user
from app.domain.auth import AuthContext
from app.domain.widget_config import WidgetSessionToken


def _make_config_dict(widget_id="wid-1"):
    return {
        "id": "cfg-1",
        "widget_id": widget_id,
        "name": "Test Widget",
        "allowed_origins": ["https://example.com"],
        "theme": "dark",
        "greeting": "Hello!",
        "position": "bottom-right",
        "enabled_tools": ["classify_issue"],
        "is_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _build_app():
    from app.api.error_handlers import register_error_handlers

    app = FastAPI()
    app.include_router(widget_loader_router)
    app.include_router(widget_public_router)
    register_error_handlers(app)
    return app


@pytest.mark.asyncio
async def test_allowed_origin_can_get_public_config():
    """A request from an allowed origin receives the public widget config."""
    app = _build_app()
    config = _make_config_dict()

    async def _mock_get_by_widget_id(widget_id, request_id=None):
        return config

    with patch("app.api.routes.widget_public._get_widget_config_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.get_by_widget_id = AsyncMock(side_effect=_mock_get_by_widget_id)
        mock_get_svc.return_value = mock_svc

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(
                "/public/widgets/wid-1/config",
                headers={"Origin": "https://example.com"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["widget_id"] == "wid-1"
            assert data["theme"] == "dark"
            assert data["greeting"] == "Hello!"
            assert data["position"] == "bottom-right"
            assert "classify_issue" in data["enabled_tools"]


@pytest.mark.asyncio
async def test_allowed_origin_can_get_session_token():
    """A request from an allowed origin receives a session token."""
    app = _build_app()
    config = _make_config_dict()

    async def _mock_get_by_widget_id(widget_id, request_id=None):
        return config

    with patch("app.api.routes.widget_public._get_widget_config_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.get_by_widget_id = AsyncMock(side_effect=_mock_get_by_widget_id)
        mock_get_svc.return_value = mock_svc

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/public/widgets/wid-1/session",
                headers={"Origin": "https://example.com"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "token" in data
            assert data["widget_id"] == "wid-1"
            assert "expires_at" in data


@pytest.mark.asyncio
async def test_loader_js_is_served():
    """GET /widget/loader.js returns JavaScript."""
    app = _build_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/widget/loader.js")
        assert resp.status_code == 200
        assert "javascript" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_frame_serves_html():
    """GET /widget/frame/{widget_id} returns HTML."""
    app = _build_app()
    config = _make_config_dict()

    async def _mock_get_by_widget_id(widget_id, request_id=None):
        return config

    with patch("app.api.routes.widget_loader._get_widget_config_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.get_by_widget_id = AsyncMock(side_effect=_mock_get_by_widget_id)
        mock_get_svc.return_value = mock_svc

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(
                "/widget/frame/wid-1",
                headers={"Origin": "https://example.com"},
            )
            assert resp.status_code == 200
            assert "html" in resp.headers.get("content-type", "")
            assert "wid-1" in resp.text
