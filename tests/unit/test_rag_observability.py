"""Unit tests for RAG observability — trace-safe redacted attributes."""

from __future__ import annotations

from app.infra.redaction import (
    redact_chunk_preview,
    redact_eval_report,
    redact_rag_prompt,
    redact_snapshot_row,
)


class TestRAGChunkPreviewRedaction:
    def test_strips_content_field(self):
        chunk = {
            "chunk_id": "c1",
            "parent_id": "p1",
            "content": "full document text that should not appear",
            "final_score": 0.9,
        }
        result = redact_chunk_preview(chunk)
        assert "chunk_id" in result
        assert "content" not in result

    def test_keeps_score_metadata(self):
        chunk = {"chunk_id": "c2", "rank": 1, "final_score": 0.85}
        result = redact_chunk_preview(chunk)
        assert result["rank"] == 1
        assert result["final_score"] == 0.85

    def test_strips_unsafe_keys(self):
        chunk = {"api_key": "sk-secret", "chunk_id": "c3"}
        result = redact_chunk_preview(chunk)
        assert "chunk_id" in result
        assert "api_key" not in result


class TestRAGPromptRedaction:
    def test_replaces_content_with_length(self):
        payload = {"content": "hello world" * 10, "chunk_id": "c1"}
        result = redact_rag_prompt(payload)
        assert "content" not in result
        assert result["content_len"] == 110

    def test_redacts_maintainer_answer(self):
        payload = {"maintainer_answer": "secret solution", "query": "test"}
        result = redact_rag_prompt(payload)
        assert "maintainer_answer" not in result
        assert result["maintainer_answer_len"] == 15

    def test_preserves_safe_keys(self):
        payload = {
            "chunk_id": "c1",
            "top_k": 5,
            "embedding_model": "all-MiniLM-L6-v2",
            "content": "secret",
        }
        result = redact_rag_prompt(payload)
        assert result["chunk_id"] == "c1"
        assert result["top_k"] == 5
        assert "content" not in result

    def test_redacts_secrets_in_safe_values(self):
        payload = {
            "chunk_id": "c1",
            "query": "sk-abcdefghijklmnopqrstuvwxyz12",
        }
        result = redact_rag_prompt(payload)
        assert "sk-" not in result["query"]


class TestSnapshotRedaction:
    def test_preserves_snapshot_metadata(self):
        row = {
            "snapshot_id": "s1",
            "conversation_id": "conv1",
            "message_id": "msg1",
            "chunk_ids": ["c1", "c2"],
            "scores": [0.9, 0.8],
            "query": "sk-abcdefghijklmnopqrstuvwxyz12345",
        }
        result = redact_snapshot_row(row)
        assert result["snapshot_id"] == "s1"
        assert result["chunk_ids"] == ["c1", "c2"]
        assert "sk-" not in result["query"]

    def test_strips_raw_content(self):
        row = {"snapshot_id": "s1", "content": "raw data", "content_preview": "preview"}
        result = redact_snapshot_row(row)
        assert "content" not in result
        assert "content_preview" not in result


class TestEvalReportRedaction:
    def test_redacts_chunk_previews_in_report(self):
        report = {
            "report_id": "r1",
            "baseline": {"mode": "baseline", "metrics": {}},
            "advanced": {"mode": "advanced", "metrics": {}},
            "chunks": [
                {"chunk_id": "c1", "content": "secret", "score": 0.9},
                {"chunk_id": "c2", "content": "secret2", "score": 0.8},
            ],
        }
        result = redact_eval_report(report)
        for chunk in result["chunks"]:
            assert "content" not in chunk
            assert "chunk_id" in chunk

    def test_strips_content_fields_from_nested(self):
        report = {"report_id": "r1", "content": "should be removed"}
        result = redact_eval_report(report)
        assert "content" not in result

    def test_redacts_secrets_in_values(self):
        report = {"report_id": "r1", "notes": "sk-abcdefghijklmnopqrstuvwxyz12 secret"}
        result = redact_eval_report(report)
        assert "sk-" not in result["notes"]
