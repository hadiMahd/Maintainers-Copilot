"""Contract tests for the Phase 7 `/chat` endpoint."""

from __future__ import annotations

import json

import pytest

from app.domain.auth import AuthContext
from app.domain.chat import ChatErrorBody, ChatExecutionResult, ChatStreamEvent
from app.domain.errors import ChatValidationError, RequestTooLargeError


def _parse_sse(body: str) -> list[dict]:
    events: list[dict] = []
    for line in body.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: ") :]))
    return events


class _StubChatService:
    def __init__(self, result=None, exc=None) -> None:
        self._result = result
        self._exc = exc

    async def execute_chat(self, *, user_id: str, body, request_id: str):
        _ = (user_id, body, request_id)
        if self._exc is not None:
            raise self._exc
        return self._result


@pytest.mark.asyncio
async def test_chat_requires_authentication(app):
    response = await app.post("/chat", json={"conversation_id": "c-1", "message": "hello"})
    assert response.status_code == 401
    body = response.json()
    assert body["error_code"] == "authentication_required"


@pytest.mark.asyncio
async def test_chat_authenticated_stream_shape(app, monkeypatch):
    fastapi_app = app._transport.app
    import app.api.routes.chat as chat_mod
    from app.api.dependencies.auth import get_current_user

    async def mock_auth(request=None, credentials=None):
        return AuthContext(user_id="user-1", email="user@test.com", role="user")

    fastapi_app.dependency_overrides[get_current_user] = mock_auth
    monkeypatch.setattr(
        chat_mod,
        "_get_chatbot_service",
        lambda request: _StubChatService(
            result=ChatExecutionResult(
                request_id="req-1",
                conversation_id="c-1",
                message_id="m-1",
                trace_id="trace-1",
                run_id="run-1",
                events=[
                    ChatStreamEvent(
                        event_type="message_delta",
                        conversation_id="c-1",
                        message_id="m-1",
                        sequence=0,
                        content="hello",
                        trace_id="trace-1",
                    ),
                    ChatStreamEvent(
                        event_type="done",
                        conversation_id="c-1",
                        message_id="m-1",
                        sequence=1,
                        content="done",
                        trace_id="trace-1",
                    ),
                ],
            )
        ),
    )

    response = await app.post("/chat", json={"conversation_id": "c-1", "message": "hello"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["x-trace-id"] == "trace-1"
    events = _parse_sse(response.text)
    assert events[0]["event_type"] == "message_delta"
    assert events[0]["conversation_id"] == "c-1"
    assert events[-1]["event_type"] == "done"
    fastapi_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_invalid_input_returns_structured_422(app, monkeypatch):
    fastapi_app = app._transport.app
    import app.api.routes.chat as chat_mod
    from app.api.dependencies.auth import get_current_user

    async def mock_auth(request=None, credentials=None):
        return AuthContext(user_id="user-1", email="user@test.com", role="user")

    fastapi_app.dependency_overrides[get_current_user] = mock_auth
    monkeypatch.setattr(
        chat_mod,
        "_get_chatbot_service",
        lambda request: _StubChatService(exc=ChatValidationError("Invalid chat request")),
    )

    response = await app.post("/chat", json={"conversation_id": "c-1", "message": "   "})
    assert response.status_code == 422
    assert response.json()["error_code"] == "invalid_chat_input"
    fastapi_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_request_too_large_returns_413(app, monkeypatch):
    fastapi_app = app._transport.app
    import app.api.routes.chat as chat_mod
    from app.api.dependencies.auth import get_current_user

    async def mock_auth(request=None, credentials=None):
        return AuthContext(user_id="user-1", email="user@test.com", role="user")

    fastapi_app.dependency_overrides[get_current_user] = mock_auth
    monkeypatch.setattr(
        chat_mod,
        "_get_chatbot_service",
        lambda request: _StubChatService(exc=RequestTooLargeError("too large")),
    )

    response = await app.post("/chat", json={"conversation_id": "c-1", "message": "hello"})
    assert response.status_code == 413
    assert response.json()["error_code"] == "request_too_large"
    fastapi_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_safe_sse_error_event_shape(app, monkeypatch):
    fastapi_app = app._transport.app
    import app.api.routes.chat as chat_mod
    from app.api.dependencies.auth import get_current_user

    async def mock_auth(request=None, credentials=None):
        return AuthContext(user_id="user-1", email="user@test.com", role="user")

    fastapi_app.dependency_overrides[get_current_user] = mock_auth
    monkeypatch.setattr(
        chat_mod,
        "_get_chatbot_service",
        lambda request: _StubChatService(
            result=ChatExecutionResult(
                request_id="req-1",
                conversation_id="c-1",
                message_id="m-1",
                trace_id="trace-1",
                events=[
                    ChatStreamEvent(
                        event_type="error",
                        conversation_id="c-1",
                        message_id="m-1",
                        sequence=0,
                        trace_id="trace-1",
                        error=ChatErrorBody(
                            code="tool_execution_failed",
                            message="Tool failed safely",
                            request_id="req-1",
                            trace_id="trace-1",
                        ),
                    ),
                    ChatStreamEvent(
                        event_type="done",
                        conversation_id="c-1",
                        message_id="m-1",
                        sequence=1,
                        content="done",
                        trace_id="trace-1",
                    ),
                ],
            )
        ),
    )

    response = await app.post("/chat", json={"conversation_id": "c-1", "message": "hello"})
    events = _parse_sse(response.text)
    assert events[0]["event_type"] == "error"
    assert events[0]["error"]["code"] == "tool_execution_failed"
    assert "traceback" not in response.text.lower()
    fastapi_app.dependency_overrides.clear()
