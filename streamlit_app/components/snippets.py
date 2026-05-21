"""Embed snippet display component."""

from __future__ import annotations

import streamlit as st

from streamlit_app.models import EmbedSnippetView


def display_embed_snippet(snippet: EmbedSnippetView) -> None:
    """Render a copyable embed snippet in a code block."""
    st.subheader("Embed Snippet")
    st.caption(f"Configuration: {snippet.widget_config_id}")
    st.code(snippet.snippet, language="html")
    st.caption("Copy the snippet above and paste it into your website.")
