"""Unit tests for Streamlit admin guard (st.navigation role-based exclusion)."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "streamlit_app"))


class _FakeSessionState(dict):
    def __getattr__(self, name):
        if name in self:
            return self[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value

    def get(self, key, default=None):
        return super().get(key, default)


class _FakePage:
    def __init__(self, page, title="", icon=""):
        self._page = page
        self.title = title
        self.icon = icon


@pytest.fixture
def patch_st():
    with patch("streamlit_app.app.st") as mock_st:
        mock_st.session_state = _FakeSessionState()
        mock_st.Page = _FakePage
        yield mock_st


def test_page_roots_includes_admin_for_admin_role(patch_st):
    patch_st.session_state["role"] = "admin"
    from streamlit_app.app import _get_page_roots

    pages = _get_page_roots()
    titles = [p.title for p in pages]
    assert "Widget Config" in titles, f"Admin pages should include Widget Config, got: {titles}"


def test_page_roots_excludes_admin_for_user_role(patch_st):
    patch_st.session_state["role"] = "user"
    from streamlit_app.app import _get_page_roots

    pages = _get_page_roots()
    titles = [p.title for p in pages]
    assert (
        "Widget Config" not in titles
    ), f"User pages should NOT include Widget Config, got: {titles}"


def test_page_roots_always_includes_chat_and_memory(patch_st):
    patch_st.session_state["role"] = "user"
    from streamlit_app.app import _get_page_roots

    pages = _get_page_roots()
    titles = [p.title for p in pages]
    assert "Chat" in titles
    assert "Memory" in titles
