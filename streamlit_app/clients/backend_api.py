"""Backend API client for Streamlit internal UI.

Single data-access path: every Streamlit call to the FastAPI backend goes
through this client.  Uses ``httpx`` with explicit timeouts from
``StreamlitSettings``.  No direct database, Redis, Vault, or model calls.
"""

from __future__ import annotations

from typing import Callable, Iterable

import httpx

from streamlit_app.config import StreamlitSettings
from streamlit_app.models import (
    ChatEventView,
    CurrentUserView,
    EmbedSnippetView,
    MemoryInspectionQuery,
    MemoryInspectionResult,
    MemoryRecordView,
    UIErrorMessage,
    WidgetConfigForm,
    WidgetConfigView,
)


def _parse_error(status_code: int, body: dict | None) -> UIErrorMessage:
    if body is None:
        body = {}
    code_map = {
        401: "authentication_required",
        403: "access_denied",
        413: "request_too_large",
        422: "validation_error",
    }
    code = code_map.get(status_code, "backend_error")
    message = body.get("message") or body.get("error", "Backend request failed")
    return UIErrorMessage(
        code=code,
        message=str(message),
        retryable=status_code >= 500,
        request_id=body.get("request_id"),
        trace_id=body.get("trace_id"),
    )


class BackendAPIClient:
    """Typed ``httpx`` client for all backend API calls."""

    def __init__(
        self,
        settings: StreamlitSettings,
        token_provider: Callable[[], str | None],
        on_auth_invalid: Callable[[], None],
    ) -> None:
        self._base = settings.base_url.rstrip("/")
        self._timeout_rest = httpx.Timeout(
            connect=settings.connect_timeout_seconds,
            read=settings.read_timeout_seconds,
            write=10.0,
            pool=5.0,
        )
        self._timeout_sse = httpx.Timeout(
            connect=settings.connect_timeout_seconds,
            read=settings.sse_timeout_seconds,
            write=10.0,
            pool=5.0,
        )
        self._token_provider = token_provider
        self._on_auth_invalid = on_auth_invalid

    def _headers(self) -> dict[str, str]:
        token = self._token_provider()
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    def _build_client(self, timeout: httpx.Timeout) -> httpx.Client:
        """Build an httpx client. Overridable in tests for transport injection."""
        return httpx.Client(timeout=timeout)

    def _handle_response(self, response: httpx.Response) -> dict:
        if response.is_success:
            return response.json()
        if response.status_code == 401:
            self._on_auth_invalid()
        body = None
        try:
            body = response.json()
        except Exception:
            pass
        error = _parse_error(response.status_code, body)
        raise BackendAPIError(error)

    def login(self, email: str, password: str) -> dict:
        with self._build_client(self._timeout_rest) as client:
            response = client.post(
                f"{self._base}/auth/login",
                json={"email": email, "password": password},
            )
            return self._handle_response(response)

    def get_current_user(self) -> CurrentUserView:
        with self._build_client(self._timeout_rest) as client:
            response = client.get(
                f"{self._base}/users/me",
                headers=self._headers(),
            )
            data = self._handle_response(response)
            return CurrentUserView(
                id=data.get("id", ""),
                email=data.get("email", ""),
                role=data.get("role", "user"),
                is_active=data.get("is_active", True),
            )

    def chat_stream(
        self, conversation_id: str, message: str
    ) -> Iterable[ChatEventView]:
        import json

        with self._build_client(self._timeout_sse) as client:
            with client.stream(
                "POST",
                f"{self._base}/chat",
                headers=self._headers(),
                json={"conversation_id": conversation_id, "message": message},
            ) as response:
                if response.status_code != 200:
                    body = None
                    try:
                        body = response.json()
                    except Exception:
                        pass
                    error = _parse_error(response.status_code, body)
                    yield ChatEventView(
                        event_type="error",
                        content=error.message,
                        error=error,
                    )
                    return
                for line in response.iter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data:"):
                        continue
                    payload = line[len("data:"):].strip()
                    if not payload:
                        continue
                    try:
                        event = json.loads(payload)
                        yield ChatEventView(
                            event_type=event.get("event_type", "message_delta"),
                            content=event.get("content", ""),
                            sequence=event.get("sequence", 0),
                            trace_id=event.get("trace_id"),
                            error=(
                                UIErrorMessage(
                                    code=event.get("code", "backend_error"),
                                    message=event.get("message", ""),
                                )
                                if event.get("event_type") == "error"
                                else None
                            ),
                        )
                    except (json.JSONDecodeError, KeyError):
                        continue

    def list_widget_configs(self) -> list[WidgetConfigView]:
        with self._build_client(self._timeout_rest) as client:
            response = client.get(
                f"{self._base}/admin/widget-configs/",
                headers=self._headers(),
            )
            data = self._handle_response(response)
            items = data.get("items", [])
            return [
                WidgetConfigView(
                    id=item.get("id", ""),
                    name=item.get("name", ""),
                    allowed_origins=item.get("allowed_origins", []),
                    theme=item.get("theme", "default"),
                    welcome_message=item.get("welcome_message"),
                    is_enabled=item.get("is_enabled", True),
                    updated_at=item.get("updated_at", ""),
                )
                for item in items
            ]

    def create_widget_config(self, form: WidgetConfigForm) -> WidgetConfigView:
        payload: dict = {
            "name": form.name,
            "allowed_origins": form.allowed_origins,
            "theme": form.theme,
            "is_enabled": form.is_enabled,
        }
        if form.welcome_message:
            payload["welcome_message"] = form.welcome_message
        with self._build_client(self._timeout_rest) as client:
            response = client.post(
                f"{self._base}/admin/widget-configs/",
                headers=self._headers(),
                json=payload,
            )
            data = self._handle_response(response)
            return WidgetConfigView(
                id=data.get("id", ""),
                name=data.get("name", ""),
                allowed_origins=data.get("allowed_origins", []),
                theme=data.get("theme", "default"),
                welcome_message=data.get("welcome_message"),
                is_enabled=data.get("is_enabled", True),
                updated_at=data.get("updated_at", ""),
            )

    def update_widget_config(
        self, config_id: str, form: WidgetConfigForm
    ) -> WidgetConfigView:
        payload: dict = {k: v for k, v in {
            "name": form.name or None,
            "allowed_origins": form.allowed_origins or None,
            "theme": form.theme or None,
            "is_enabled": form.is_enabled,
            "welcome_message": form.welcome_message or None,
        }.items() if v is not None}
        with self._build_client(self._timeout_rest) as client:
            response = client.patch(
                f"{self._base}/admin/widget-configs/{config_id}",
                headers=self._headers(),
                json=payload,
            )
            data = self._handle_response(response)
            return WidgetConfigView(
                id=data.get("id", ""),
                name=data.get("name", ""),
                allowed_origins=data.get("allowed_origins", []),
                theme=data.get("theme", "default"),
                welcome_message=data.get("welcome_message"),
                is_enabled=data.get("is_enabled", True),
                updated_at=data.get("updated_at", ""),
            )

    def get_embed_snippet(self, config_id: str) -> EmbedSnippetView:
        with self._build_client(self._timeout_rest) as client:
            response = client.get(
                f"{self._base}/admin/widget-configs/{config_id}/embed-snippet",
                headers=self._headers(),
            )
            data = self._handle_response(response)
            return EmbedSnippetView(
                widget_config_id=data.get("widget_config_id", ""),
                snippet=data.get("snippet", ""),
                generated_at=data.get("generated_at", ""),
            )

    def inspect_memory(self, query: MemoryInspectionQuery) -> MemoryInspectionResult:
        params: dict = {"limit": query.limit}
        if query.memory_type:
            params["memory_type"] = query.memory_type
        if query.search_text:
            params["search_text"] = query.search_text
        with self._build_client(self._timeout_rest) as client:
            response = client.get(
                f"{self._base}/memory/long-term",
                headers=self._headers(),
                params=params,
            )
            data = self._handle_response(response)
            items = [
                MemoryRecordView(
                    id=item.get("id", ""),
                    owner_user_id=item.get("owner_user_id", ""),
                    memory_type=item.get("memory_type", ""),
                    redacted_content=item.get("redacted_content", ""),
                    source=item.get("source", ""),
                    created_at=item.get("created_at", ""),
                )
                for item in data.get("items", [])
            ]
            return MemoryInspectionResult(
                items=items,
                next_cursor=data.get("next_cursor"),
                scope=data.get("scope", "own"),
            )


class BackendAPIError(Exception):
    """Wraps a backend error into a typed UI error."""

    def __init__(self, ui_error: UIErrorMessage) -> None:
        super().__init__(ui_error.message)
        self.ui_error = ui_error
