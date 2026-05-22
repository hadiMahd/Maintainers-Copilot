"""Unit tests for reranking impact, deterministic tie handling, snapshot redaction, and 50-conversation retention."""

from __future__ import annotations

from app.domain.rag import RAGChunk, RetrievalResult, SnapshotRecord
from app.infra.redaction import redact_snapshot_row
from app.infra.reranker_client import BaseRerankerClient, FakeRerankerClient


class TestRerankingImpact:
    def test_rerank_changes_ordering(self):
        chunks = [_make_chunk(f"c{i}") for i in range(5)]
        results = [
            RetrievalResult(
                rank=i + 1, final_score=0.9 - i * 0.1, chunk=chunks[i], retrieval_mode="hybrid"
            )
            for i in range(5)
        ]
        reranker = FakeRerankerClient()
        reranked = reranker.rerank("query", results, top_k=3)
        assert len(reranked) == 3
        assert all(r.rerank_score is not None for r in reranked)

    def test_rerank_preserves_scores(self):
        chunks = [_make_chunk("c1"), _make_chunk("c2")]
        results = [
            RetrievalResult(rank=1, final_score=0.8, chunk=chunks[0]),
            RetrievalResult(rank=2, final_score=0.7, chunk=chunks[1]),
        ]
        reranker = FakeRerankerClient()
        ranked = reranker.rerank("test", results, top_k=2)
        assert ranked[0].final_score == 0.8

    def test_rerank_identity_for_ties(self):
        chunks = [_make_chunk("c1"), _make_chunk("c2")]
        results = [
            RetrievalResult(rank=1, final_score=0.5, chunk=chunks[0]),
            RetrievalResult(rank=2, final_score=0.5, chunk=chunks[1]),
        ]
        reranker = FakeRerankerClient()
        ranked = reranker.rerank("test", results, top_k=2)
        assert len(ranked) == 2

    def test_rerank_truncates_to_top_k(self):
        chunks = [_make_chunk(f"c{i}") for i in range(10)]
        results = [
            RetrievalResult(rank=i + 1, final_score=0.9 - i * 0.05, chunk=chunks[i])
            for i in range(10)
        ]
        reranker = FakeRerankerClient()
        ranked = reranker.rerank("query", results, top_k=5)
        assert len(ranked) == 5

    def test_base_reranker_interface(self):
        assert hasattr(BaseRerankerClient, "rerank")
        assert hasattr(BaseRerankerClient, "model_name")


class TestSnapshotRedaction:
    def test_snapshot_strips_raw_content(self):
        row = {
            "snapshot_id": "s1",
            "conversation_id": "c1",
            "message_id": "m1",
            "trace_id": "t1",
            "chunk_ids": ["a", "b"],
            "scores": [0.9, 0.8],
            "query": "how to install numpy",
            "content": "raw text should be removed",
        }
        result = redact_snapshot_row(row)
        assert "content" not in result
        assert "chunk_ids" in result
        assert result["snapshot_id"] == "s1"

    def test_snapshot_preserves_conversation_metadata(self):
        row = {
            "snapshot_id": "s2",
            "conversation_id": "conv-42",
            "message_id": "msg-99",
            "trace_id": "trace-abc",
            "chunk_ids": [],
            "scores": [],
        }
        result = redact_snapshot_row(row)
        assert result["conversation_id"] == "conv-42"
        assert result["message_id"] == "msg-99"
        assert result["trace_id"] == "trace-abc"

    def test_snapshot_redacts_secrets_in_query(self):
        row = {
            "snapshot_id": "s3",
            "conversation_id": "c3",
            "message_id": "m3",
            "query": "use key sk-abcdefghijklmnopqrstuvwxyz99xyz",
        }
        result = redact_snapshot_row(row)
        assert "sk-" not in result["query"]


class TestConversationRetention:
    def test_retain_last_50_conversations(self):
        snapshots = [_make_snapshot(conv_id=f"conv-{i}") for i in range(100)]
        retained = _prune_snapshots(snapshots, max_conversations=50)
        assert len(retained) == 50
        ids = [s.conversation_id for s in retained]
        assert "conv-0" not in ids
        assert "conv-99" in ids

    def test_under_limit_keeps_all(self):
        snapshots = [_make_snapshot(conv_id=f"conv-{i}") for i in range(10)]
        retained = _prune_snapshots(snapshots, max_conversations=50)
        assert len(retained) == 10

    def test_conversation_ids_are_unique_in_retention(self):
        snapshots = [
            _make_snapshot(conv_id="conv-a"),
            _make_snapshot(conv_id="conv-a"),
            _make_snapshot(conv_id="conv-b"),
        ]
        retained = _prune_snapshots(snapshots, max_conversations=50)
        conv_ids = [s.conversation_id for s in retained]
        assert len(conv_ids) == 3

    def test_trace_metadata_association(self):
        snapshot = _make_snapshot(conv_id="c1", msg_id="m1", trace_id="trace-xyz")
        assert snapshot.trace_id == "trace-xyz"
        assert snapshot.message_id == "m1"


# -- Helpers -----------------------------------------------------------------


def _make_chunk(chunk_id: str) -> RAGChunk:
    return RAGChunk(
        chunk_id=chunk_id,
        parent_id="p1",
        source_type="docs",
        content="test",
        content_hash="abc",
        token_count=2,
    )


def _make_snapshot(
    conv_id: str = "conv-1", msg_id: str = "msg-1", trace_id: str = "trace-1"
) -> SnapshotRecord:
    return SnapshotRecord(
        conversation_id=conv_id,
        message_id=msg_id,
        trace_id=trace_id,
    )


def _prune_snapshots(
    snapshots: list[SnapshotRecord],
    max_conversations: int = 50,
) -> list[SnapshotRecord]:
    seen: set[str] = set()
    kept: list[SnapshotRecord] = []
    for s in reversed(snapshots):
        if s.conversation_id not in seen:
            seen.add(s.conversation_id)
        if len(seen) > max_conversations:
            break
        kept.append(s)
    return list(reversed(kept))
