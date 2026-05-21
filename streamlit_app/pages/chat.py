"""Authenticated chat page.

Requires authenticated session state.  Sends messages to the backend
``POST /chat`` SSE endpoint and renders the streaming response with
``st.write_stream()``.  Never buffers the full response before display.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

streamlit_app_dir = Path(__file__).resolve().parent.parent
if str(streamlit_app_dir) not in sys.path:
    sys.path.insert(0, str(streamlit_app_dir))

from streamlit_app.clients.backend_api import BackendAPIClient, BackendAPIError
from streamlit_app.components.auth import clear_auth, get_token, init_auth_state
from streamlit_app.components.errors import display_error
from streamlit_app.config import StreamlitSettings
from streamlit_app.models import ChatEventView

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
    token_provider=get_token,
    on_auth_invalid=clear_auth,
)

st.title("Chat")
st.caption("Ask a maintainer question — the assistant will classify, extract, summarise, and answer.")

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "chat_pending" not in st.session_state:
    st.session_state.chat_pending = False

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

    full_response = ""
    trace_id = None

    def event_generator():
        nonlocal full_response, trace_id
        for event in stream:
            if event.trace_id:
                trace_id = event.trace_id
            if event.event_type == "error":
                yield event
                return
            if event.event_type in ("message_delta", "done"):
                full_response += event.content
            yield event

    with st.chat_message("assistant"):
        try:
            st.write_stream(event_generator())
        except Exception:
            if full_response:
                st.markdown(full_response)
            else:
                st.error("Chat response interrupted.")

    if full_response:
        st.session_state.chat_messages.append({"role": "assistant", "content": full_response})
    if trace_id:
        st.caption(f"Trace: {trace_id}")

    st.session_state.chat_pending = False
