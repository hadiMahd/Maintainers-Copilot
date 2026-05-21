"""Authenticated chat page.

Requires authenticated session state.  Sends messages to the backend
``POST /chat`` SSE endpoint and renders the streaming response with
``st.write_stream()``.  Never buffers the full response before display.
"""

from __future__ import annotations

import sys
from pathlib import Path
import uuid

import streamlit as st

streamlit_app_dir = Path(__file__).resolve().parent.parent
if str(streamlit_app_dir) not in sys.path:
    sys.path.insert(0, str(streamlit_app_dir))

from streamlit_app.clients.backend_api import BackendAPIClient, BackendAPIError
from streamlit_app.components.auth import clear_auth, init_auth_state
from streamlit_app.components.errors import display_error
from streamlit_app.config import StreamlitSettings
from streamlit_app.models import ChatEventView, UIErrorMessage

init_auth_state()

if not st.session_state.get("is_authenticated"):
    st.warning("Please log in to use the chat.")
    st.stop()


@st.cache_resource
def get_settings() -> StreamlitSettings:
    settings = StreamlitSettings()
    settings.validate_or_raise()
    return settings


settings = get_settings()
client = BackendAPIClient(
    settings=settings,
    token_provider=lambda: st.session_state.get("auth_token"),
    on_auth_invalid=clear_auth,
)

st.title("Chat")
st.caption("Ask a maintainer question — the assistant will classify, extract, summarise, and answer.")

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "chat_pending" not in st.session_state:
    st.session_state.chat_pending = False
if "conversation_id" not in st.session_state or not st.session_state.conversation_id:
    st.session_state.conversation_id = uuid.uuid4().hex

for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Type your message...", disabled=st.session_state.chat_pending):
    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    st.session_state.chat_pending = True

    try:
        stream = client.chat_stream(
            conversation_id=st.session_state.get("conversation_id", ""),
            message=prompt,
        )
    except BackendAPIError as exc:
        display_error(exc.ui_error)
        st.session_state.chat_pending = False
        st.stop()
    except Exception:
        st.error("Unable to reach the chat backend. Please try again later.")
        st.session_state.chat_pending = False
        st.stop()

    full_response_parts: list[str] = []
    trace_id_holder = {"value": None}
    error_holder = {"value": None}
    warning_messages: list[str] = []
    tool_status_messages: list[str] = []

    def event_generator():
        for event in stream:
            if event.trace_id:
                trace_id_holder["value"] = event.trace_id
            if event.event_type == "error":
                error_holder["value"] = event.error or UIErrorMessage(
                    code="backend_error",
                    message=event.content or "Backend request failed",
                )
                return
            if event.event_type == "warning" and event.content:
                warning_messages.append(event.content)
                continue
            if event.event_type == "tool_status" and event.content:
                tool_status_messages.append(event.content)
                continue
            if event.event_type == "message_delta" and event.content:
                full_response_parts.append(event.content)
                yield event.content
                continue
            if event.event_type == "done":
                return

    with st.chat_message("assistant"):
        try:
            st.write_stream(event_generator())
        except Exception:
            full_response = "".join(full_response_parts)
            if full_response:
                st.markdown(full_response)
            else:
                st.error("Chat response interrupted.")
        for tool_status in tool_status_messages:
            st.caption(tool_status)
        for warning in warning_messages:
            st.warning(warning)
        if error_holder["value"] is not None:
            display_error(error_holder["value"])

    full_response = "".join(full_response_parts)
    if full_response:
        st.session_state.chat_messages.append({"role": "assistant", "content": full_response})
    if trace_id_holder["value"]:
        st.caption(f"Trace: {trace_id_holder['value']}")

    st.session_state.chat_pending = False
