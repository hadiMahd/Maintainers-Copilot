"""Unit tests for chat SSE streaming and embed snippet display."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "streamlit_app"))

from streamlit_app.models import ChatEventView, EmbedSnippetView, UIErrorMessage


def test_chat_event_view_parses_delta():
    event = ChatEventView(event_type="message_delta", content="Hello", sequence=1, trace_id="tr-1")
    assert event.event_type == "message_delta"
    assert event.content == "Hello"
    assert event.sequence == 1
    assert event.trace_id == "tr-1"
    assert event.error is None


def test_chat_event_view_parses_error():
    err = UIErrorMessage(code="backend_error", message="fail")
    event = ChatEventView(event_type="error", content="fail", error=err)
    assert event.event_type == "error"
    assert event.error.code == "backend_error"


def test_embed_snippet_view_fields():
    snippet = EmbedSnippetView(
        widget_config_id="wc-1",
        snippet='<script data-mc-widget-config="wc-1"></script>',
        generated_at="2026-01-01T00:00:00Z",
    )
    assert snippet.widget_config_id == "wc-1"
    assert "wc-1" in snippet.snippet


def test_embed_snippet_not_mutated():
    """Verify the snippet content is passed through as-is."""
    from streamlit_app.components.snippets import display_embed_snippet
    snippet = EmbedSnippetView(
        widget_config_id="cfg-x",
        snippet='<script src="widget/loader.js"></script>',
    )
    with patch("streamlit_app.components.snippets.st") as mock_st:
        display_embed_snippet(snippet)
        code_calls = [c for c in mock_st.code.call_args_list if c[0]]
        if code_calls:
            rendered = code_calls[0][0][0]
            assert "loader.js" in rendered
            assert "cfg-x" not in rendered  # config ID in snippet content, not mutated
