"""Unit tests for Streamlit auth session lifecycle."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "streamlit_app"))

from streamlit_app.models import CurrentUserView
from streamlit_app.components.auth import set_authenticated, clear_auth, init_auth_state


class _FakeSessionState(dict):
    """Dict that also supports attribute access like Streamlit's st.session_state."""

    def __getattr__(self, name):
        if name in self:
            return self[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value


@pytest.fixture
def mock_cookies():
    cookies = {}
    with (
        patch("streamlit_app.components.auth.CookieManager") as mock_cm,
        patch("streamlit_app.components.auth.st") as mock_st,
    ):
        mock_st.session_state = _FakeSessionState()

        instance = MagicMock()
        instance.ready.return_value = True
        instance.__contains__ = lambda self, k: k in cookies
        instance.__getitem__ = lambda self, k: cookies.get(k)
        instance.__setitem__ = lambda self, k, v: cookies.update({k: v})
        instance.__delitem__ = lambda self, k: cookies.pop(k, None)
        mock_cm.return_value = instance
        yield {"cookies": cookies, "mock_st": mock_st, "mock_cm": mock_cm}


def test_init_auth_state_sets_defaults(mock_cookies):
    mock_st = mock_cookies["mock_st"]
    init_auth_state()
    assert mock_st.session_state["is_authenticated"] is False
    assert mock_st.session_state["current_user"] is None
    assert mock_st.session_state["role"] == "user"


def test_set_authenticated_populates_state_and_cookie(mock_cookies):
    init_auth_state()
    user = CurrentUserView(id="u1", email="u@t.com", role="admin", is_active=True)
    set_authenticated(user, "tok-123")

    mock_st = mock_cookies["mock_st"]
    assert mock_st.session_state["is_authenticated"] is True
    assert mock_st.session_state["current_user"].id == "u1"
    assert mock_st.session_state["role"] == "admin"
    assert mock_cookies["cookies"]["mc_access_token"] == "tok-123"


def test_clear_auth_resets_state(mock_cookies):
    init_auth_state()
    user = CurrentUserView(id="u1", email="u@t.com", role="user")
    set_authenticated(user, "tok-456")

    clear_auth()

    mock_st = mock_cookies["mock_st"]
    assert mock_st.session_state["is_authenticated"] is False
    assert mock_st.session_state["current_user"] is None
    assert mock_st.session_state["role"] == "user"
    assert "mc_access_token" not in mock_cookies["cookies"]
