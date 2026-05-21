"""Admin widget configuration page.

Requires authenticated session state and admin role.  Lists, creates, and
edits widget configurations through backend API calls.  Displays generated
embed snippets.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

streamlit_app_dir = Path(__file__).resolve().parent.parent
if str(streamlit_app_dir) not in sys.path:
    sys.path.insert(0, str(streamlit_app_dir))

from streamlit_app.clients.backend_api import BackendAPIClient, BackendAPIError
from streamlit_app.components.auth import clear_auth, init_auth_state
from streamlit_app.components.errors import display_error
from streamlit_app.components.snippets import display_embed_snippet
from streamlit_app.config import StreamlitSettings
from streamlit_app.models import WidgetConfigForm

init_auth_state()

if not st.session_state.get("is_authenticated"):
    st.warning("Please log in to access this page.")
    st.stop()

if st.session_state.get("role") != "admin":
    st.error("Access denied. This page is only available to administrators.")
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

st.title("Widget Configuration")

tab_list, tab_create = st.tabs(["Configurations", "New Configuration"])

with tab_list:
    st.subheader("Existing Configurations")
    try:
        configs = client.list_widget_configs()
    except BackendAPIError as exc:
        display_error(exc.ui_error)
        configs = []
    except Exception:
        st.error("Unable to load widget configurations.")
        configs = []

    if not configs:
        st.info("No widget configurations yet. Create one in the other tab.")
    else:
        for cfg in configs:
            with st.expander(f"{cfg.name} ({'enabled' if cfg.is_enabled else 'disabled'})"):
                st.json({
                    "ID": cfg.id,
                    "Name": cfg.name,
                    "Origins": cfg.allowed_origins,
                    "Theme": cfg.theme,
                    "Welcome": cfg.welcome_message,
                    "Enabled": cfg.is_enabled,
                    "Updated": cfg.updated_at,
                })
                col_edit, col_snippet = st.columns(2)
                with col_edit:
                    if st.button(f"Edit {cfg.name}", key=f"edit_{cfg.id}"):
                        st.session_state.edit_config_id = cfg.id
                        st.rerun()
                with col_snippet:
                    if st.button(f"Snippet {cfg.name}", key=f"snippet_{cfg.id}"):
                        st.session_state.snippet_config_id = cfg.id
                        st.rerun()

with tab_create:
    st.subheader("Create / Edit Configuration")
    edit_id = st.session_state.get("edit_config_id", "")
    snippet_id = st.session_state.get("snippet_config_id", "")

    if snippet_id:
        try:
            snippet = client.get_embed_snippet(snippet_id)
            display_embed_snippet(snippet)
        except BackendAPIError as exc:
            display_error(exc.ui_error)
        except Exception:
            st.error("Unable to generate embed snippet.")
        if st.button("Close Snippet"):
            st.session_state.pop("snippet_config_id", None)
            st.rerun()
    else:
        with st.form("widget_config_form"):
            name = st.text_input("Name", max_chars=120, placeholder="My Widget")
            origins_text = st.text_area(
                "Allowed Origins (one per line)",
                placeholder="https://example.com",
                help="Each origin on its own line.",
            )
            theme = st.selectbox("Theme", ["default", "light", "dark"])
            welcome = st.text_area("Welcome Message", max_chars=500, placeholder="Hello! How can I help?")
            is_enabled = st.checkbox("Enabled", value=True)
            submitted = st.form_submit_button("Save" if edit_id else "Create")

            if submitted:
                if not name:
                    st.error("Name is required.")
                elif not origins_text.strip():
                    st.error("At least one allowed origin is required.")
                else:
                    origins = [o.strip() for o in origins_text.split("\n") if o.strip()]
                    form = WidgetConfigForm(
                        name=name,
                        allowed_origins=origins,
                        theme=theme,
                        welcome_message=welcome or None,
                        is_enabled=is_enabled,
                    )
                    try:
                        if edit_id:
                            client.update_widget_config(edit_id, form)
                            st.success("Configuration updated.")
                            st.session_state.pop("edit_config_id", None)
                        else:
                            client.create_widget_config(form)
                            st.success("Configuration created.")
                        st.rerun()
                    except BackendAPIError as exc:
                        display_error(exc.ui_error)
                    except Exception:
                        st.error("Unable to save widget configuration.")
