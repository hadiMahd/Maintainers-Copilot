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
                        "name": "W1",
                        "allowed_origins": ["https://example.com"],
                        "theme": "default",
                        "welcome_message": None,
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
