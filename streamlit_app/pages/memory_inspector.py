"""Memory inspector page.

Requires authenticated session state.  Reads memory records only through
backend memory-inspection endpoints.  Shows only backend-authorized,
backend-redacted fields.  Does not store returned memory records outside
transient Streamlit session state.
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
from streamlit_app.models import MemoryInspectionQuery

init_auth_state()

if not st.session_state.get("is_authenticated"):
    st.warning("Please log in to access this page.")
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

st.title("Memory Inspector")
st.caption("Inspect your authorised long-term memory records.")

is_admin = st.session_state.get("role") == "admin"

with st.form("memory_filter_form"):
    cols = st.columns(3)
    with cols[0]:
        memory_type = st.selectbox(
            "Memory Type",
            ["", "episodic", "semantic", "procedural"],
            format_func=lambda x: x.capitalize() if x else "All",
        )
    with cols[1]:
        limit = st.number_input("Limit", min_value=1, max_value=100, value=25)
    with cols[2]:
        submitted = st.form_submit_button("Search")

if submitted:
    query = MemoryInspectionQuery(
        scope="admin" if is_admin else "own",
        memory_type=memory_type or None,
        limit=limit,
    )

    try:
        result = client.inspect_memory(query)
    except BackendAPIError as exc:
        display_error(exc.ui_error)
        result = None
    except Exception:
        st.error("Unable to inspect memory. Please try again later.")
        result = None

    if result is not None:
        st.caption(f"Scope: {result.scope}  |  Records: {len(result.items)}")
        if not result.items:
            st.info("No memory records found.")
        else:
            for record in result.items:
                with st.expander(
                    f"{record.memory_type.capitalize()} — {record.source or 'unknown'} "
                    f"({record.created_at[:10]})"
                ):
                    st.markdown(record.redacted_content)
                    if is_admin and record.owner_user_id:
                        st.caption(f"Owner: {record.owner_user_id}")
            if result.next_cursor:
                st.caption("More records available. Refine your filter to see older entries.")
