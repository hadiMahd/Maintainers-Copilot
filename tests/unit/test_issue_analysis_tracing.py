"""Unit tests for issue-analysis tracing hooks and request_id/trace_id propagation."""

from __future__ import annotations

from app.infra.redaction import redact_issue_analysis_metadata


class TestTraceIdPropagation:
    def test_request_id_present_in_ner_response(self):
        meta = {
            "request_id": "ner-req-1",
            "tool_name": "ner",
            "entity_count": 3,
            "combined_characters": 100,
        }
        safe = redact_issue_analysis_metadata(meta)
        assert safe["request_id"] == "ner-req-1"

    def test_request_id_present_in_summarization_response(self):
        meta = {
            "request_id": "sum-req-2",
            "tool_name": "summarization",
            "status": "ok",
        }
        safe = redact_issue_analysis_metadata(meta)
        assert safe["request_id"] == "sum-req-2"

    def test_trace_id_safe_in_metadata(self):
        meta = {
            "trace_id": "trace-abc-123",
            "tool_name": "ner",
        }
        safe = redact_issue_analysis_metadata(meta)
        assert safe["trace_id"] == "trace-abc-123"

    def test_provider_credentials_never_in_trace(self):
        meta = {
            "tool_name": "summarization",
            "api_key": "sk-secret-do-not-leak",
            "endpoint": "https://secret.openai.azure.com",
        }
        safe = redact_issue_analysis_metadata(meta)
        assert "api_key" not in safe
        assert "endpoint" not in safe

    def test_redacted_fake_secrets_not_in_output(self):
        meta = {
            "request_id": "req-1",
            "token": "fake-token-that-looks-like-sk-sensitive",
            "password": "should-be-removed",
        }
        safe = redact_issue_analysis_metadata(meta)
        assert "token" not in safe
        assert "password" not in safe
        assert "request_id" in safe
