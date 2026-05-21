"""Unit tests for BackendAPIClient with mocked httpx transport."""

import json
from unittest.mock import patch

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


def _make_client(settings, handler, token="fake-token", on_invalid=None):
    """Return a BackendAPIClient whose _build_client returns a mocked client."""
    c = BackendAPIClient(
        settings=settings,
        token_provider=lambda: token,
        on_auth_invalid=on_invalid or (lambda: None),
    )
    mock_client = httpx.Client(transport=httpx.MockTransport(handler))
    c._build_client = lambda timeout: mock_client
    return c


def test_login_calls_backend(settings):
    def handler(request):
        body = json.loads(request.content)
        return httpx.Response(
            200,
            json={"access_token": "tok-abc", "refresh_token": "rt-abc", "token_type": "bearer"},
        )

    c = _make_client(settings, handler, token=None)
    data = c.login("user@test.com", "secret123")
    assert data["access_token"] == "tok-abc"


def test_login_invalid_credentials_raises(settings):
    invalidated = []

    def handler(request):
        return httpx.Response(401, json={"message": "Invalid credentials"})

    c = _make_client(settings, handler, token=None, on_invalid=lambda: invalidated.append(True))
    with pytest.raises(BackendAPIError) as exc:
        c.login("bad@test.com", "wrong")
    assert exc.value.ui_error.code == "authentication_required"
    assert len(invalidated) == 1


def test_get_current_user_sends_auth_header(settings):
    def handler(request):
        assert request.headers["Authorization"] == "Bearer fake-token"
        return httpx.Response(200, json={"id": "u1", "email": "u@t.com", "role": "admin", "is_active": True})

    c = _make_client(settings, handler)
    user = c.get_current_user()
    assert user.id == "u1"
    assert user.role == "admin"


def test_list_widget_configs_parses_response(settings):
    def handler(request):
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "wc-1",
                        "widget_id": "wid-abc",
                        "name": "W1",
                        "allowed_origins": ["https://example.com"],
                        "theme": "dark",
                        "greeting": "Hello!",
                        "position": "bottom-right",
                        "enabled_tools": ["classify_issue", "write_memory"],
                        "is_enabled": True,
                        "updated_at": "2026-01-01T00:00:00Z",
                    }
                ]
            },
        )

    c = _make_client(settings, handler)
    configs = c.list_widget_configs()
    assert len(configs) == 1
    assert configs[0].id == "wc-1"
    assert configs[0].widget_id == "wid-abc"
    assert configs[0].greeting == "Hello!"
    assert configs[0].position == "bottom-right"
    assert configs[0].enabled_tools == ["classify_issue", "write_memory"]


def test_list_widget_configs_parses_missing_phase9_fields(settings):
    """Backward compatibility: missing Phase 9 fields get defaults."""
    def handler(request):
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "wc-1",
                        "name": "W1",
                        "allowed_origins": ["https://example.com"],
                        "theme": "light",
                        "is_enabled": True,
                        "updated_at": "2026-01-01T00:00:00Z",
                    }
                ]
            },
        )

    c = _make_client(settings, handler)
    configs = c.list_widget_configs()
    assert len(configs) == 1
    assert configs[0].widget_id == ""
    assert configs[0].greeting is None
    assert configs[0].position == "bottom-right"
    assert configs[0].enabled_tools == []


def test_create_widget_config_sends_phase9_fields(settings):
    """Create payload must include greeting, position, enabled_tools."""
    captured_payload = {}

    def handler(request):
        nonlocal captured_payload
        captured_payload = json.loads(request.content) if request.content else {}
        return httpx.Response(
            201,
            json={
                "id": "wc-new",
                "widget_id": "wid-xyz",
                "name": captured_payload.get("name", ""),
                "allowed_origins": captured_payload.get("allowed_origins", []),
                "theme": captured_payload.get("theme", "light"),
                "greeting": captured_payload.get("greeting"),
                "position": captured_payload.get("position", "bottom-right"),
                "enabled_tools": captured_payload.get("enabled_tools", []),
                "is_enabled": True,
                "updated_at": "2026-01-01T00:00:00Z",
                "created_at": "2026-01-01T00:00:00Z",
            },
        )

    c = _make_client(settings, handler)
    form = WidgetConfigForm(
        name="New Widget",
        allowed_origins=["https://example.com"],
        theme="dark",
        greeting="Hi there",
        position="bottom-left",
        enabled_tools=["classify_issue"],
        is_enabled=True,
    )
    cfg = c.create_widget_config(form)
    assert cfg.widget_id == "wid-xyz"
    assert cfg.greeting == "Hi there"
    assert cfg.position == "bottom-left"
    assert captured_payload.get("greeting") == "Hi there"
    assert captured_payload.get("position") == "bottom-left"
    assert captured_payload.get("enabled_tools") == ["classify_issue"]


def test_update_widget_config_sends_phase9_fields(settings):
    """Update payload must include Phase 9 fields when provided."""
    captured_payload = {}

    def handler(request):
        nonlocal captured_payload
        captured_payload = json.loads(request.content) if request.content else {}
        return httpx.Response(
            200,
            json={
                "id": "wc-1",
                "widget_id": "wid-abc",
                "name": captured_payload.get("name", ""),
                "allowed_origins": captured_payload.get("allowed_origins", []),
                "theme": captured_payload.get("theme", "light"),
                "greeting": captured_payload.get("greeting"),
                "position": captured_payload.get("position", "bottom-right"),
                "enabled_tools": captured_payload.get("enabled_tools", []),
                "is_enabled": True,
                "updated_at": "2026-01-01T00:00:00Z",
                "created_at": "2026-01-01T00:00:00Z",
            },
        )

    c = _make_client(settings, handler)
    form = WidgetConfigForm(
        name="Updated",
        theme="dark",
        greeting="Updated greeting",
        position="top-left",
        enabled_tools=["write_memory"],
        is_enabled=False,
    )
    cfg = c.update_widget_config("wc-1", form)
    assert cfg.greeting == "Updated greeting"
    assert captured_payload.get("greeting") == "Updated greeting"
    assert captured_payload.get("position") == "top-left"
    assert captured_payload.get("enabled_tools") == ["write_memory"]


def test_delete_widget_config_calls_backend(settings):
    """Delete must send DELETE request and handle response."""
    call_log = []

    def handler(request):
        call_log.append((request.method, request.url.path))
        return httpx.Response(200, json={"id": "wc-1", "widget_id": "wid-abc", "deleted_at": "2026-01-01T00:00:00Z"})

    c = _make_client(settings, handler)
    c.delete_widget_config("wc-1")
    assert call_log[0] == ("DELETE", "/admin/widget-configs/wc-1")


def test_delete_widget_config_raises_on_error(settings):
    """Delete must raise BackendAPIError on non-2xx response."""

    def handler(request):
        return httpx.Response(404, json={"message": "Not found"})

    c = _make_client(settings, handler)
    with pytest.raises(BackendAPIError) as exc:
        c.delete_widget_config("wc-nonexistent")
    assert exc.value.ui_error.code == "backend_error"


def test_inspect_memory_parses_response(settings):
    def handler(request):
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
                    }
                ],
                "scope": "own",
            },
        )

    c = _make_client(settings, handler)
    result = c.inspect_memory(MemoryInspectionQuery(limit=5))
    assert len(result.items) == 1
    assert result.items[0].redacted_content == "[REDACTED]"
    assert result.scope == "own"
