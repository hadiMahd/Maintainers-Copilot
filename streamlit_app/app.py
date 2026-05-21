"""Streamlit internal chatbot and admin app entry point.

Thin presentation layer — all data access goes through BackendAPIClient.
Uses st.navigation() with runtime role-based page list: admin-only pages
are excluded from the navigation menu for regular users.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

streamlit_app_dir = Path(__file__).resolve().parent
if str(streamlit_app_dir) not in sys.path:
    sys.path.insert(0, str(streamlit_app_dir))

from streamlit_app.clients.backend_api import BackendAPIClient, BackendAPIError
from streamlit_app.components.auth import (
    clear_auth,
    get_token,
    init_auth_state,
    login_form,
    restore_session,
    set_authenticated,
)
from streamlit_app.components.errors import display_error
from streamlit_app.config import StreamlitSettings
from streamlit_app.models import CurrentUserView

st.set_page_config(page_title="Maintainer's Copilot", layout="wide")


@st.cache_resource
def get_settings() -> StreamlitSettings:
    settings = StreamlitSettings()
    settings.validate_or_raise()
    return settings


def _build_client() -> BackendAPIClient:
    return BackendAPIClient(
        settings=get_settings(),
        token_provider=get_token,
        on_auth_invalid=clear_auth,
    )


def _login_callback(email: str, password: str) -> None:
    client = _build_client()
    try:
        data = client.login(email, password)
    except BackendAPIError as exc:
        display_error(exc.ui_error)
        return
    except Exception:
        st.error("Unable to reach the backend. Please try again later.")
        return

    token = data.get("access_token", "")
    if not token:
        st.error("Login succeeded but no token was returned.")
        return

    try:
        user = client.get_current_user()
    except BackendAPIError as exc:
        display_error(exc.ui_error)
        return
    except Exception:
        st.error("Unable to fetch user profile.")
        return

    set_authenticated(user, token)
    st.rerun()


def _validate_and_restore(token: str) -> None:
    client = BackendAPIClient(
        settings=get_settings(),
        token_provider=lambda: token,
        on_auth_invalid=clear_auth,
    )
    try:
        user = client.get_current_user()
    except (BackendAPIError, Exception):
        clear_auth()
        raise
    if not st.session_state.get("is_authenticated"):
        set_authenticated(user, token)


def _get_page_roots() -> list[st.Page]:
    """Build the page list based on current user role.

    Admin-only pages are excluded from the list for regular users.
    """
    pages: list[st.Page] = [
        st.Page("pages/chat.py", title="Chat", icon="💬"),
        st.Page("pages/memory_inspector.py", title="Memory", icon="🧠"),
    ]
    role = st.session_state.get("role", "user")
    if role == "admin":
        pages.append(
            st.Page("pages/admin_widget_config.py", title="Widget Config", icon="⚙️")
        )
    return pages


def _show_logout_button() -> None:
    cols = st.columns([1, 1, 1, 1, 1])
    with cols[4]:
        if st.button("Log out"):
            clear_auth()
            st.rerun()


def main() -> None:
    init_auth_state()

    if not st.session_state.is_authenticated:
        if not restore_session(_validate_and_restore):
            login_form(_login_callback)
            return

    _show_logout_button()
    pages = _get_page_roots()
    pg = st.navigation(pages)
    pg.run()


if __name__ == "__main__":
    main()
