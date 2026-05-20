"""Unit tests for RAG redaction."""

from __future__ import annotations

import pytest

from app.infra.redaction import (
    redact_chunk_preview,
    redact_rag_prompt,
    redact_snapshot_row,
    redact_eval_report,
)


class TestChunkContentRedaction:
    def test_full_content_replaced_by_preview(self):
        chunk = {
            "chunk_id": "c1",
            "parent_id": "p1",
            "content": "a" * 1000,
            "content_hash": "abc",
            "score": 0.9,
        }
        result = redact_chunk_preview(chunk)
        assert "content" not in result
        assert "chunk_id" in result

    def test_keeps_required_metadata(self):
        chunk = {
            "chunk_id": "c2",
            "source_type": "docs",
            "retrieval_mode": "hybrid",
            "content": "should not appear",
        }
        result = redact_chunk_preview(chunk)
        assert result["chunk_id"] == "c2"
        assert result["source_type"] == "docs"


class TestPromptRedaction:
    def test_content_replaced_with_length(self):
        payload = {
            "query": "how to install",
            "content": "install numpy with pip install numpy pandas",
        }
        result = redact_rag_prompt(payload)
        assert "content" not in result
        assert result["content_len"] == len(payload["content"])

    def test_redacts_secret_pattern_in_strings(self):
        payload = {
            "query": "sk-abcdefghijklmnopqrstuvwxyz12345 query about secrets",
        }
        result = redact_rag_prompt(payload)
        assert "sk-" not in result["query"]
        assert "[REDACTED]" in result["query"]

    def test_preserves_numeric_and_bool(self):
        payload = {
            "top_k": 5,
            "insufficient_evidence": False,
            "score": 0.95,
            "content": "remove me",
        }
        result = redact_rag_prompt(payload)
        assert result["top_k"] == 5
        assert result["insufficient_evidence"] is False
        assert result["score"] == 0.95
        assert "content" not in result


class TestSnapshotRedaction:
    def test_preserves_chunk_ids(self):
        row = {
            "snapshot_id": "s1",
            "conversation_id": "c1",
            "message_id": "m1",
            "chunk_ids": ["chunk-a", "chunk-b"],
            "scores": [0.9, 0.85],
        }
        result = redact_snapshot_row(row)
        assert result["chunk_ids"] == ["chunk-a", "chunk-b"]
        assert result["scores"] == [0.9, 0.85]

    def test_redacts_query(self):
        row = {
            "snapshot_id": "s2",
            "conversation_id": "c2",
            "message_id": "m2",
            "query": "sk-abcdefghijklmnopqrstuvwxyz99 secret query",
        }
        result = redact_snapshot_row(row)
        assert "sk-" not in result["query"]


class TestEvalReportRedaction:
    def test_strips_content_from_chunks(self):
        report = {
            "report_id": "r1",
            "baseline": {"mode": "baseline", "judge_id": "j1"},
            "advanced": {"mode": "advanced", "judge_id": "j1"},
            "results": [
                {"chunk_id": "c1", "content": "long text" * 100, "score": 0.9},
            ],
        }
        result = redact_eval_report(report)
        for item in result["results"]:
            assert "content" not in item
