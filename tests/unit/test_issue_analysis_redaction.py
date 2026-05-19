"""Unit tests for issue-analysis log, trace metadata, and fake-secret redaction."""

from __future__ import annotations

import pytest

from app.infra.redaction import (
    redact_issue_analysis_metadata,
    redact_log_payload,
)


class TestRedactIssueAnalysisMetadata:
    def test_keeps_safe_keys(self):
        meta = {
            "request_id": "req-1",
            "tool_name": "ner",
            "combined_characters": 100,
            "entity_count": 5,
            "entity_types": ["file_path", "class_name"],
            "status": "ok",
        }
        result = redact_issue_analysis_metadata(meta)
        assert result["request_id"] == "req-1"
        assert result["tool_name"] == "ner"
        assert result["combined_characters"] == 100
        assert result["entity_count"] == 5

    def test_strips_unsafe_keys(self):
        meta = {
            "title": "secret content",
            "body": "should not appear",
            "api_key": "sk-secret",
            "request_id": "req-2",
        }
        result = redact_issue_analysis_metadata(meta)
        assert "request_id" in result
        assert "title" not in result
        assert "body" not in result
        assert "api_key" not in result

    def test_redacts_secret_patterns_in_safe_values(self):
        meta = {
            "request_id": "req-with-sk-abcdefghijklmnopqrstuvwxyz1234567",
            "status": "ok",
        }
        result = redact_issue_analysis_metadata(meta)
        assert "sk-" not in result["request_id"]

    def test_handles_empty_metadata(self):
        result = redact_issue_analysis_metadata({})
        assert result == {}

    def test_preserves_numeric_fields(self):
        meta = {"combined_characters": 42, "entity_count": 3}
        result = redact_issue_analysis_metadata(meta)
        assert result["combined_characters"] == 42
        assert result["entity_count"] == 3


class TestRedactLogPayload:
    def test_replaces_title_with_length(self):
        payload = {"title": "Hello World", "body": None}
        result = redact_log_payload(payload)
        assert "title" not in result
        assert result["title_len"] == 11

    def test_replaces_body_with_length(self):
        payload = {"body": "test body content"}
        result = redact_log_payload(payload)
        assert "body" not in result
        assert result["body_len"] == 17

    def test_replaces_comments_with_metadata(self):
        payload = {"comments": ["hello", "world"]}
        result = redact_log_payload(payload)
        assert "comments" not in result
        assert result["comments_len"] == 2
        assert result["comments_count"] == 10

    def test_preserves_non_content_fields(self):
        payload = {"request_id": "req-999", "title": "secret"}
        result = redact_log_payload(payload)
        assert result["request_id"] == "req-999"
        assert "title" not in result
        assert result["title_len"] == 6

    def test_redacts_secrets_in_other_fields(self):
        payload = {
            "request_id": "req-ok",
            "title": "test",
            "extra": "sk-abcdefghijklmnopqrstuvwxyz12",
        }
        result = redact_log_payload(payload)
        assert "sk-" not in result["extra"]
