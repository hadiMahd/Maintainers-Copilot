"""Integration test for blocked-origin embed flow."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI

from app.api.routes.widget_loader import router as widget_loader_router
from app.api.routes.widget_public import router as widget_public_router
from app.api.error_handlers import register_error_handlers


def _make_config_dict(widget_id="wid-1"):
    return {
        "id": "cfg-1",
        "widget_id": widget_id,
        "name": "Test Widget",
        "allowed_origins": ["https://example.com"],
        "theme": "dark",
        "greeting": "Hello!",
        "position": "bottom-right",
        "enabled_tools": [],
        "is_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _build_app():
    app = FastAPI()
    app.include_router(widget_loader_router)
    app.include_router(widget_public_router)
    register_error_handlers(app)
    return app


@pytest.mark.asyncio
async def test_blocked_origin_cannot_get_public_config():
    """A request from a blocked origin is denied public config."""
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
                headers={"Origin": "https://evil.com"},
            )
            assert resp.status_code == 403


@pytest.mark.asyncio
async def test_blocked_origin_cannot_get_session_token():
    """A request from a blocked origin is denied session token."""
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
                headers={"Origin": "https://evil.com"},
            )
            assert resp.status_code == 403


@pytest.mark.asyncio
async def test_no_origin_cannot_get_public_config():
    """A request with no Origin header is denied."""
    app = _build_app()
    config = _make_config_dict()

    async def _mock_get_by_widget_id(widget_id, request_id=None):
        return config

    with patch("app.api.routes.widget_public._get_widget_config_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.get_by_widget_id = AsyncMock(side_effect=_mock_get_by_widget_id)
        mock_get_svc.return_value = mock_svc

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/public/widgets/wid-1/config")
            assert resp.status_code == 403


@pytest.mark.asyncio
async def test_disabled_widget_cannot_get_config():
    """A disabled widget denies config even from allowed origin."""
    app = _build_app()
    config = _make_config_dict()
    config["is_enabled"] = False

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
            assert resp.status_code == 403
