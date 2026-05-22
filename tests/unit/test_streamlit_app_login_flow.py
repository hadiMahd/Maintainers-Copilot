"""Unit tests for Streamlit app login callback flow."""

from __future__ import annotations

import importlib

from streamlit_app.models import CurrentUserView


class _FakeLoginClient:
    def __init__(self) -> None:
        self.called_with: tuple[str, str] | None = None

    def login(self, email: str, password: str) -> dict:
        self.called_with = (email, password)
        return {
            "access_token": "tok-123",
            "refresh_token": "rt-123",
            "token_type": "bearer",
        }


class _FakeProfileClient:
    def __init__(self, token_provider) -> None:
        self._token_provider = token_provider

    def get_current_user(self) -> CurrentUserView:
        token = self._token_provider()
        assert token == "tok-123"
        return CurrentUserView(
            id="u1",
            email="admin@ex.com",
            role="admin",
            is_active=True,
        )


def test_login_callback_fetches_profile_with_fresh_token(monkeypatch):
    app = importlib.import_module("streamlit_app.app")

    login_client = _FakeLoginClient()
    captured: dict[str, object] = {}
    cookies = object()

    monkeypatch.setattr(
        app,
        "_build_client",
        lambda token_provider=None, on_auth_invalid=None: (
            login_client if token_provider is None else _FakeProfileClient(token_provider)
        ),
    )
    monkeypatch.setattr(
        app,
        "set_authenticated",
        lambda user, token, cookie_manager: captured.update(
            {"user": user, "token": token, "cookies": cookie_manager}
        ),
    )
    monkeypatch.setattr(app.st, "rerun", lambda: captured.update({"rerun": True}))
    monkeypatch.setattr(app.st, "error", lambda message: captured.update({"error": message}))

    app._login_callback("admin@ex.com", "123", cookies)

    assert login_client.called_with == ("admin@ex.com", "123")
    assert captured["token"] == "tok-123"
    assert captured["cookies"] is cookies
    assert captured["user"].email == "admin@ex.com"
    assert captured["user"].role == "admin"
    assert captured["rerun"] is True
    assert "error" not in captured
