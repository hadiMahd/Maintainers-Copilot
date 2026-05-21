"""Integration test for widget chat submission plus EventSource stream."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI

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


def _make_chat_events():
    from app.domain.chat import ChatStreamEvent
    return [
        ChatStreamEvent(
            event_type="message_delta",
            conversation_id="conv-1",
            sequence=1,
            content="Hello",
            trace_id="tr-abc123",
        ),
        ChatStreamEvent(
            event_type="message_delta",
            conversation_id="conv-1",
            sequence=2,
            content=" world",
            trace_id="tr-abc123",
        ),
        ChatStreamEvent(
            event_type="done",
            conversation_id="conv-1",
            sequence=3,
            content="",
            trace_id="tr-abc123",
        ),
    ]


def _build_app():
    app = FastAPI()
    app.include_router(widget_public_router)
    register_error_handlers(app)
    return app


@pytest.mark.asyncio
async def test_submit_message_returns_conversation_id():
    """POST /public/widgets/{id}/chat/messages returns a conversation_id."""
    app = _build_app()
    config = _make_config_dict()

    async def _mock_get_by_widget_id(widget_id, request_id=None):
        return config

    mock_chat_svc = MagicMock()
    mock_chat_svc.submit_message = AsyncMock(return_value="conv-1")

    with patch("app.api.routes.widget_public._get_widget_config_service") as mock_get_svc, \
         patch("app.api.routes.widget_public._get_widget_chat_service") as mock_get_chat:
        mock_svc = MagicMock()
        mock_svc.get_by_widget_id = AsyncMock(side_effect=_mock_get_by_widget_id)
        mock_get_svc.return_value = mock_svc
        mock_get_chat.return_value = mock_chat_svc

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/public/widgets/wid-1/chat/messages",
                json={"message": "Hello", "session_token": "tok-1"},
                headers={"Origin": "https://example.com"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["conversation_id"] == "conv-1"


@pytest.mark.asyncio
async def test_submit_message_does_not_put_text_on_url():
    """The message submission endpoint must not include raw text in the URL."""
    app = _build_app()
    config = _make_config_dict()

    async def _mock_get_by_widget_id(widget_id, request_id=None):
        return config

    captured_urls = []
    original_post = httpx.AsyncClient.post

    async def _capture_post(self, url, *args, **kwargs):
        captured_urls.append(str(url))
        return await original_post(self, url, *args, **kwargs)

    mock_chat_svc = MagicMock()
    mock_chat_svc.submit_message = AsyncMock(return_value="conv-1")

    with patch("app.api.routes.widget_public._get_widget_config_service") as mock_get_svc, \
         patch("app.api.routes.widget_public._get_widget_chat_service") as mock_get_chat:
        mock_svc = MagicMock()
        mock_svc.get_by_widget_id = AsyncMock(side_effect=_mock_get_by_widget_id)
        mock_get_svc.return_value = mock_svc
        mock_get_chat.return_value = mock_chat_svc

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/public/widgets/wid-1/chat/messages",
                json={"message": "secret message content", "session_token": "tok-1"},
                headers={"Origin": "https://example.com"},
            )
            assert resp.status_code == 200

    for url in captured_urls:
        assert "secret" not in url
        assert "message+" not in url.lower()


@pytest.mark.asyncio
async def test_stream_chat_reuses_phase7_event_shape():
    """GET /public/widgets/{id}/chat/stream emits SSE events matching Phase 7 shape."""
    import app.api.routes.widget_public as wp_mod

    app = _build_app()
    config = _make_config_dict()

    async def _mock_get_by_widget_id(widget_id, request_id=None):
        return config

    events = _make_chat_events()
    result = MagicMock()
    result.events = events

    mock_chat_svc = MagicMock()
    mock_chat_svc.submit_message = AsyncMock(return_value="conv-1")
    mock_chat_svc.execute_chat = AsyncMock(return_value=result)

    from app.services.widget_chat_service import WidgetChatService
    widget_chat = WidgetChatService(chatbot_service=mock_chat_svc)

    with patch("app.api.routes.widget_public._get_widget_config_service") as mock_get_svc, \
         patch("app.api.routes.widget_public._get_widget_chat_service") as mock_get_chat:
        mock_svc = MagicMock()
        mock_svc.get_by_widget_id = AsyncMock(side_effect=_mock_get_by_widget_id)
        mock_get_svc.return_value = mock_svc
        mock_get_chat.return_value = widget_chat

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            wp_mod._pending_messages["conv-1"] = "test message"
            resp = await ac.get(
                "/public/widgets/wid-1/chat/stream",
                params={"token": "tok-1", "conversation_id": "conv-1"},
                headers={"Origin": "https://example.com"},
            )
            assert resp.status_code == 200
            text = resp.text

            lines = [l for l in text.split('\n') if l.startswith('data: ')]
            assert len(lines) >= 3

            first_event = json.loads(lines[0][6:])
            assert first_event["event_type"] == "message_delta"
            assert "conversation_id" in first_event
            assert "sequence" in first_event
            assert "content" in first_event

            done_event = json.loads(lines[-1][6:])
            assert done_event["event_type"] == "done"


@pytest.mark.asyncio
async def test_stream_events_include_trace_id_when_safe():
    """SSE stream events must include trace_id for browser-visible correlation."""
    import app.api.routes.widget_public as wp_mod

    app = _build_app()
    config = _make_config_dict()

    async def _mock_get_by_widget_id(widget_id, request_id=None):
        return config

    events = _make_chat_events()
    result = MagicMock()
    result.events = events

    mock_chat_svc = MagicMock()
    mock_chat_svc.execute_chat = AsyncMock(return_value=result)

    from app.services.widget_chat_service import WidgetChatService
    widget_chat = WidgetChatService(chatbot_service=mock_chat_svc)

    with patch("app.api.routes.widget_public._get_widget_config_service") as mock_get_svc, \
         patch("app.api.routes.widget_public._get_widget_chat_service") as mock_get_chat:
        mock_svc = MagicMock()
        mock_svc.get_by_widget_id = AsyncMock(side_effect=_mock_get_by_widget_id)
        mock_get_svc.return_value = mock_svc
        mock_get_chat.return_value = widget_chat

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            wp_mod._pending_messages["conv-1"] = "test"
            resp = await ac.get(
                "/public/widgets/wid-1/chat/stream",
                params={"token": "tok-1", "conversation_id": "conv-1"},
                headers={"Origin": "https://example.com"},
            )
            assert resp.status_code == 200
            text = resp.text

            lines = [l for l in text.split('\n') if l.startswith('data: ')]
            first_event = json.loads(lines[0][6:])
            assert "trace_id" in first_event
            assert first_event["trace_id"] == "tr-abc123"


@pytest.mark.asyncio
async def test_stream_url_does_not_contain_raw_message():
    """The SSE stream URL must not contain raw message content."""
    import app.api.routes.widget_public as wp_mod

    app = _build_app()
    config = _make_config_dict()

    async def _mock_get_by_widget_id(widget_id, request_id=None):
        return config

    events = _make_chat_events()
    result = MagicMock()
    result.events = events

    mock_chat_svc = MagicMock()
    mock_chat_svc.execute_chat = AsyncMock(return_value=result)

    from app.services.widget_chat_service import WidgetChatService
    widget_chat = WidgetChatService(chatbot_service=mock_chat_svc)

    with patch("app.api.routes.widget_public._get_widget_config_service") as mock_get_svc, \
         patch("app.api.routes.widget_public._get_widget_chat_service") as mock_get_chat:
        mock_svc = MagicMock()
        mock_svc.get_by_widget_id = AsyncMock(side_effect=_mock_get_by_widget_id)
        mock_get_svc.return_value = mock_svc
        mock_get_chat.return_value = widget_chat

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            wp_mod._pending_messages["conv-1"] = "secret content"
            resp = await ac.get(
                "/public/widgets/wid-1/chat/stream",
                params={"token": "tok-1", "conversation_id": "conv-1"},
                headers={"Origin": "https://example.com"},
            )
            assert resp.status_code == 200
            url = str(resp.url)
            assert "secret" not in url
            assert "message=" not in url
