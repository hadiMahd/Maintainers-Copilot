"""Shared error display component.

Maps UIErrorMessage codes to appropriate Streamlit display severity.
"""

from __future__ import annotations

import streamlit as st

from streamlit_app.models import UIErrorMessage

ERROR_DISPLAY_MAP = {
    "authentication_required": ("error", True),
    "access_denied": ("error", False),
    "validation_error": ("warning", False),
    "request_too_large": ("warning", False),
    "backend_timeout": ("warning", True),
    "backend_unavailable": ("warning", True),
    "backend_error": ("error", False),
}


def display_error(error: UIErrorMessage | None) -> None:
    """Display a clean user-facing error message.

    Never renders stack traces, tokens, or raw payloads.
    """
    if error is None:
        return

    severity, retry_hint = ERROR_DISPLAY_MAP.get(error.code, ("error", False))

    message = error.message
    if retry_hint:
        message = f"{message}  You can try again."

    if severity == "error":
        st.error(message)
    else:
        st.warning(message)
