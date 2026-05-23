"""Integration test: full Streamlit client-to-backend flow.

Covers login → profile → chat SSE → widget CRUD → embed snippet →
memory inspection → error handling, all through BackendAPIClient
with mocked httpx transport.
"""

import json

import httpx
import pytest

from streamlit_app.clients.backend_api import BackendAPIClient, BackendAPIError
from streamlit_app.config import StreamlitSettings
from streamlit_app.models import MemoryInspectionQuery, WidgetConfigForm


@pytest.fixture
def settings():
    return StreamlitSettings(
        base_url="http://test.local",
        rest_timeout_seconds=30,
        sse_timeout_seconds=70,
        connect_timeout_seconds=5,
        read_timeout_seconds=30,
    )


def _build_test_client(response_fn):
    """Build a BackendAPIClient with a mock transport that uses response_fn."""
    token_store = {"token": None}
    invalidation_calls = []

    def on_invalid():
        invalidation_calls.append(True)
        token_store["token"] = None

    def _factory(timeout):
        return httpx.Client(transport=httpx.MockTransport(response_fn))

    c = BackendAPIClient(
        settings=StreamlitSettings(
            base_url="http://test.local",
            rest_timeout_seconds=30,
            sse_timeout_seconds=70,
        ),
        token_provider=lambda: token_store["token"],
        on_auth_invalid=on_invalid,
    )
    c._build_client = _factory
    return c, token_store, invalidation_calls


# ── Route dispatchers ──────────────────────────────────────────────


def _make_dispatcher(routes: dict):
    """Factory: return a handler that dispatches by method+path."""

    def handler(request: httpx.Request) -> httpx.Response:
        key = (request.method, request.url.path)
        if key in routes:
            return routes[key](request)
        return httpx.Response(404, json={"message": "Not found"})

    return handler


# ── Full-flow test ────────────────────────────────────────────────


def test_full_login_chat_widget_memory_flow(settings):
    """End-to-end: login, get profile, chat stream, widget CRUD, snippet,
    memory inspect, error handling."""

    widget_store: dict[str, dict] = {}
    call_log: list[str] = []

    def dispatch(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        method = request.method

        # ── Auth ──
        if method == "POST" and path == "/auth/login":
            body = json.loads(request.content) if request.content else {}
            if body.get("email") == "user@test.com" and body.get("password") == "secret":
                call_log.append("login_ok")
                return httpx.Response(
                    200,
                    json={
                        "access_token": "tok-integration",
                        "refresh_token": "rt",
                        "token_type": "bearer",
                    },
                )
            call_log.append("login_fail")
            return httpx.Response(401, json={"message": "Invalid credentials"})

        # ── Users ──
        if method == "GET" and path == "/users/me":
            if request.headers.get("Authorization") == "Bearer tok-integration":
                call_log.append("profile_ok")
                return httpx.Response(
                    200,
                    json={
                        "id": "u1",
                        "email": "user@test.com",
                        "role": "admin",
                        "is_active": True,
                    },
                )
            call_log.append("profile_unauth")
            return httpx.Response(401, json={"message": "Unauthenticated"})

        # ── Chat SSE ──
        if method == "POST" and path == "/chat":
            body = json.loads(request.content) if request.content else {}
            if body.get("message"):
                call_log.append("chat_stream")
                stream_body = (
                    'data: {"event_type":"message_delta","content":"Hello","sequence":1}\n\n'
                    'data: {"event_type":"message_delta","content":" world","sequence":2}\n\n'
                    'data: {"event_type":"done","content":"","sequence":3,"trace_id":"tr-1"}\n\n'
                )
                return httpx.Response(
                    200, content=stream_body.encode(), headers={"content-type": "text/event-stream"}
                )
            return httpx.Response(422, json={"message": "Empty message"})

        # ── Widget Configs ──
        if method == "GET" and path == "/admin/widget-configs/":
            call_log.append("widget_list")
            items = [{"id": k, **v} for k, v in widget_store.items()]
            return httpx.Response(200, json={"items": items})

        if method == "POST" and path == "/admin/widget-configs/":
            body = json.loads(request.content) if request.content else {}
            wid = f"wc-{len(widget_store) + 1}"
            cfg = {
                "name": body.get("name", ""),
                "allowed_origins": body.get("allowed_origins", []),
                "theme": body.get("theme", "light"),
                "greeting": body.get("greeting"),
                "position": body.get("position", "bottom-right"),
                "enabled_tools": body.get("enabled_tools", []),
                "is_enabled": body.get("is_enabled", True),
            }
            widget_store[wid] = cfg
            call_log.append("widget_create")
            return httpx.Response(
                201,
                json={
                    "id": wid,
                    "widget_id": f"wid-{wid}",
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:00:00Z",
                    **cfg,
                },
            )

        if method == "PATCH" and path.startswith("/admin/widget-configs/"):
            wid = path.split("/")[-1]
            if wid not in widget_store:
                return httpx.Response(404, json={"message": "Not found"})
            body = json.loads(request.content) if request.content else {}
            widget_store[wid].update({k: v for k, v in body.items() if v is not None})
            call_log.append("widget_update")
            return httpx.Response(
                200,
                json={
                    "id": wid,
                    "widget_id": f"wid-{wid}",
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:00:00Z",
                    **widget_store[wid],
                },
            )

        if method == "DELETE" and path.startswith("/admin/widget-configs/"):
            wid = path.split("/")[-1]
            if wid not in widget_store:
                return httpx.Response(404, json={"message": "Not found"})
            del widget_store[wid]
            call_log.append("widget_delete")
            return httpx.Response(
                200,
                json={
                    "id": wid,
                    "widget_id": f"wid-{wid}",
                    "deleted_at": "2026-01-01T00:00:00Z",
                },
            )

        # ── Embed Snippet ──
        if method == "GET" and "/embed-snippet" in path:
            wid = path.split("/")[-2] if len(path.split("/")) > 2 else ""
            if wid not in widget_store:
                return httpx.Response(404, json={"message": "Not found"})
            call_log.append("embed_snippet")
            return httpx.Response(
                200,
                json={
                    "widget_config_id": wid,
                    "snippet": f'<!-- Maintainer Copilot Widget (id: wid-{wid}) -->\n<script src="BASE_URL/widget.js" data-widget-id="wid-{wid}"></script>',
                    "generated_at": "2026-01-01T00:00:00Z",
                },
            )

        # ── Memory Inspector ──
        if method == "GET" and path == "/memory/long-term":
            call_log.append("memory_inspect")
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "mem-1",
                            "owner_user_id": "u1",
                            "memory_type": "semantic",
                            "redacted_content": "[REDACTED]",
                            "source": "chat",
                            "created_at": "2026-01-01T00:00:00Z",
                        },
                        {
                            "id": "mem-2",
                            "owner_user_id": "u2",
                            "memory_type": "episodic",
                            "redacted_content": "[REDACTED]",
                            "source": "issue",
                            "created_at": "2026-01-01T00:00:00Z",
                        },
                    ],
                    "scope": "own",
                },
            )

        return httpx.Response(500, json={"message": "Unexpected"})

    c, token_store, invalidated = _build_test_client(dispatch)

    # 1. Login with wrong password
    with pytest.raises(BackendAPIError) as exc:
        c.login("user@test.com", "wrong")
    assert exc.value.ui_error.code == "authentication_required"
    assert "login_fail" in call_log

    # 2. Login with correct credentials
    data = c.login("user@test.com", "secret")
    assert data["access_token"] == "tok-integration"
    token_store["token"] = "tok-integration"
    assert "login_ok" in call_log

    # 3. Get current user
    user = c.get_current_user()
    assert user.id == "u1"
    assert user.role == "admin"
    assert "profile_ok" in call_log

    # 4. Chat stream
    events = list(c.chat_stream("conv-1", "Hello!"))
    assert len(events) >= 2
    content = "".join(e.content for e in events if e.event_type == "message_delta")
    assert "Hello" in content
    assert any(e.trace_id == "tr-1" for e in events)
    assert "chat_stream" in call_log

    # 5. Create widget config
    form = WidgetConfigForm(
        name="MyWidget",
        allowed_origins=["https://a.com"],
        theme="dark",
        greeting="Hi!",
        position="bottom-left",
        enabled_tools=["classify_issue"],
    )
    cfg = c.create_widget_config(form)
    assert cfg.id.startswith("wc-")
    assert cfg.name == "MyWidget"
    assert cfg.widget_id.startswith("wid-")
    assert cfg.greeting == "Hi!"
    assert cfg.position == "bottom-left"
    assert "widget_create" in call_log

    # 6. List widget configs
    configs = c.list_widget_configs()
    assert len(configs) == 1
    assert "widget_list" in call_log

    # 7. Update widget config
    updated = c.update_widget_config(cfg.id, WidgetConfigForm(name="Renamed"))
    assert updated.name == "Renamed"
    assert "widget_update" in call_log

    # 8. Get embed snippet
    snippet = c.get_embed_snippet(cfg.id)
    assert "wid-" + cfg.id in snippet.snippet
    assert "/widget.js" in snippet.snippet
    assert "data-widget-id" in snippet.snippet
    assert "embed_snippet" in call_log

    # 9. Delete widget config
    c.delete_widget_config(cfg.id)
    assert "widget_delete" in call_log
    configs_after = c.list_widget_configs()
    assert len(configs_after) == 0

    # 10. Inspect memory
    result = c.inspect_memory(MemoryInspectionQuery(limit=5))
    assert len(result.items) == 2
    assert result.scope == "own"
    assert "memory_inspect" in call_log

    # 11. 401 invalidates session
    token_store["token"] = "bad-token"
    with pytest.raises(BackendAPIError):
        c.get_current_user()
    assert len(invalidated) > 0
    assert "profile_unauth" in call_log


def test_backend_timeout_maps_to_exception(settings):
    """A transport-level timeout should raise httpx.TimeoutException."""

    def handler(request):
        raise httpx.TimeoutException("timed out")

    c, _, _ = _build_test_client(handler)
    with pytest.raises(httpx.TimeoutException):
        c.get_current_user()


def test_chat_stream_error_event_yields_error_event(settings):
    """Non-200 SSE response yields a single error ChatEventView."""

    def handler(request):
        return httpx.Response(
            422,
            json={
                "error_code": "invalid_chat_input",
                "message": "Conversation ID and message must be non-empty",
            },
        )

    c, token_store, _ = _build_test_client(handler)
    token_store["token"] = "t"
    events = list(c.chat_stream("c1", "msg"))
    assert len(events) == 1
    assert events[0].event_type == "error"
    assert events[0].error is not None
    assert events[0].error.message == "Conversation ID and message must be non-empty"


def test_inspect_memory_empty_result(settings):
    def handler(request):
        return httpx.Response(200, json={"items": [], "scope": "own"})

    c, token_store, _ = _build_test_client(handler)
    token_store["token"] = "t"
    result = c.inspect_memory(MemoryInspectionQuery(limit=5))
    assert len(result.items) == 0
    assert result.scope == "own"
