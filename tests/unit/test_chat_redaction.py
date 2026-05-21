"""Unit tests for Phase 7 chat redaction helpers."""

from __future__ import annotations

from app.infra.redaction import (
    redact_chat_message,
    redact_chat_prompt_payload,
    redact_llm_payload,
    redact_sse_event,
    redact_tool_payload,
    redact_trace_metadata,
)


def test_chat_redaction_helpers_strip_fake_secrets():
    secret = "api_key=sk-abcdefghijklmnopqrstuvwxyz123456"
    assert "sk-" not in redact_chat_message(secret)
    assert "sk-" not in str(redact_chat_prompt_payload({"system_prompt": secret}))
    assert "sk-" not in str(redact_tool_payload({"content": secret}))
    assert "sk-" not in str(redact_llm_payload({"response": secret}))
    assert "sk-" not in str(redact_sse_event({"content": secret, "error": {"message": secret}}))
    assert "sk-" not in str(redact_trace_metadata({"payload": secret}))
