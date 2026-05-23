"""Integration test for widget frame response headers (CSP frame-ancestors)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI

from app.api.error_handlers import register_error_handlers
from app.api.routes.widget_loader import loader_alias_router
from app.api.routes.widget_loader import router as widget_loader_router
from app.api.routes.widget_public import router as widget_public_router


def _make_config_dict(widget_id="wid-1", origins=None):
    if origins is None:
        origins = ["https://example.com"]
    return {
        "id": "cfg-1",
        "widget_id": widget_id,
        "name": "Test Widget",
        "allowed_origins": origins,
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
async def test_frame_includes_csp_frame_ancestors():
    """The widget frame response must include CSP frame-ancestors header."""
    app = _build_app()

    async def _mock_get_by_widget_id(widget_id, request_id=None):
        return _make_config_dict(widget_id=widget_id)

    with patch("app.api.routes.widget_loader._get_widget_config_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.get_by_widget_id = AsyncMock(side_effect=_mock_get_by_widget_id)
        mock_get_svc.return_value = mock_svc

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/widget/frame/wid-1",
                headers={"Origin": "https://example.com"},
            )
            assert resp.status_code == 200
            csp = resp.headers.get("Content-Security-Policy", "")
            assert "frame-ancestors" in csp


@pytest.mark.asyncio
async def test_frame_csp_includes_allowed_origins():
    """CSP frame-ancestors must include the widget's allowed origins."""
    app = _build_app()

    async def _mock_get_by_widget_id(widget_id, request_id=None):
        return _make_config_dict(
            widget_id=widget_id, origins=["https://example.com", "https://other.com"]
        )

    with patch("app.api.routes.widget_loader._get_widget_config_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.get_by_widget_id = AsyncMock(side_effect=_mock_get_by_widget_id)
        mock_get_svc.return_value = mock_svc

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/widget/frame/wid-1",
                headers={"Origin": "https://example.com"},
            )
            assert resp.status_code == 200
            csp = resp.headers.get("Content-Security-Policy", "")
            assert "https://example.com" in csp
            assert "https://other.com" in csp


@pytest.mark.asyncio
async def test_frame_available_from_alias_router():
    """The frame path is available even if the loader alias router is included alone."""
    app = FastAPI()
    app.include_router(loader_alias_router)
    register_error_handlers(app)

    async def _mock_get_by_widget_id(widget_id, request_id=None):
        return _make_config_dict(widget_id=widget_id)

    with patch("app.api.routes.widget_loader._get_widget_config_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.get_by_widget_id = AsyncMock(side_effect=_mock_get_by_widget_id)
        mock_get_svc.return_value = mock_svc

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/widget/frame/wid-1",
                headers={"Origin": "https://example.com"},
            )
            assert resp.status_code == 200
            assert "frame-ancestors" in resp.headers.get("Content-Security-Policy", "")


@pytest.mark.asyncio
async def test_frame_blocked_origin_returns_403():
    """Frame request from blocked origin must return 403."""
    app = _build_app()

    async def _mock_get_by_widget_id(widget_id, request_id=None):
        return _make_config_dict(widget_id=widget_id, origins=["https://example.com"])

    with patch("app.api.routes.widget_loader._get_widget_config_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.get_by_widget_id = AsyncMock(side_effect=_mock_get_by_widget_id)
        mock_get_svc.return_value = mock_svc

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/widget/frame/wid-1",
                headers={"Origin": "https://evil.com"},
            )
            assert resp.status_code == 403


@pytest.mark.asyncio
async def test_public_config_has_no_store_cache():
    """Public config endpoint must use Cache-Control: no-store."""
    app = _build_app()

    async def _mock_get_by_widget_id(widget_id, request_id=None):
        return _make_config_dict()

    with patch("app.api.routes.widget_public._get_widget_config_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.get_by_widget_id = AsyncMock(side_effect=_mock_get_by_widget_id)
        mock_get_svc.return_value = mock_svc

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/public/widgets/wid-1/config",
                headers={"Origin": "https://example.com"},
            )
            assert resp.status_code == 200
            assert "no-store" in resp.headers.get("Cache-Control", "")


@pytest.mark.asyncio
async def test_response_includes_request_id():
    """Responses should include X-Request-ID header."""
    app = _build_app()

    async def _mock_get_by_widget_id(widget_id, request_id=None):
        return _make_config_dict()

    with patch("app.api.routes.widget_public._get_widget_config_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.get_by_widget_id = AsyncMock(side_effect=_mock_get_by_widget_id)
        mock_get_svc.return_value = mock_svc

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/public/widgets/wid-1/config",
                headers={"Origin": "https://example.com"},
            )
            assert resp.status_code == 200
            assert "X-Request-ID" in resp.headers
