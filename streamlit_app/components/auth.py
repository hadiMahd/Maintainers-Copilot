"""Authentication components for Streamlit internal UI.

Manages login form, cookie-backed token storage via streamlit-cookies-manager,
session restoration on page refresh, and logout.
"""

from __future__ import annotations

import streamlit as st
from streamlit_cookies_manager import CookieManager

from streamlit_app.models import CurrentUserView, LoginCredentials

TOKEN_COOKIE = "mc_access_token"


def get_cookie_manager() -> CookieManager:
    """Return the cookie manager bound to the current Streamlit context."""
    cookies = CookieManager()
    if not cookies.ready():
        st.stop()
    return cookies


def init_auth_state() -> None:
    """Initialise authentication state in st.session_state if not present."""
    defaults = {
        "is_authenticated": False,
        "current_user": None,
        "role": "user",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def store_token(cookies: CookieManager, token: str) -> None:
    """Store the access token in a browser cookie."""
    cookies[TOKEN_COOKIE] = token
    cookies.save()


def get_token() -> str | None:
    """Retrieve the access token from the cookie."""
    cookies = get_cookie_manager()
    return cookies.get(TOKEN_COOKIE)


def clear_auth() -> None:
    """Clear cookie and session state on logout or auth failure."""
    cookies = get_cookie_manager()
    if TOKEN_COOKIE in cookies:
        del cookies[TOKEN_COOKIE]
        cookies.save()
    st.session_state.is_authenticated = False
    st.session_state.current_user = None
    st.session_state.role = "user"


def set_authenticated(user: CurrentUserView, token: str) -> None:
    """Populate session state and cookie after successful login."""
    cookies = get_cookie_manager()
    store_token(cookies, token)
    st.session_state.is_authenticated = True
    st.session_state.current_user = user
    st.session_state.role = user.role


def login_form(on_submit: callable) -> None:
    """Render the login form.  ``on_submit`` is called with (email, password)."""
    st.title("Maintainer's Copilot")
    st.subheader("Log in")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Log in", type="primary"):
        if not email or not password:
            st.error("Email and password are required.")
            return
        on_submit(email, password)


def restore_session(on_validate_token: callable) -> bool:
    """Attempt to restore a session from the cookie on page load.

    Returns True if the session was successfully restored.
    """
    token = get_token()
    if not token:
        return False
    try:
        on_validate_token(token)
        return True
    except Exception:
        clear_auth()
        return False
