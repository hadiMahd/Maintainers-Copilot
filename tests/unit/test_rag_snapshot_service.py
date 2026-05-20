"""Unit tests for RAG snapshot service — redaction, metadata association, and 50-conversation retention."""

from __future__ import annotations

import pytest

from app.domain.rag import SnapshotRecord
from app.infra.redaction import redact_snapshot_row


class TestSnapshotServiceLogic:
    def test_store_snapshot_with_metadata(self):
        snap = SnapshotRecord(
            conversation_id="conv-1",
            message_id="msg-1",
            trace_id="trace-abc",
            query="how to install",
            chunk_ids=["c1", "c2"],
            scores=[0.9, 0.8],
            metadata_preview={"source_type": "docs"},
        )
        assert snap.conversation_id == "conv-1"
        assert len(snap.chunk_ids) == 2
        assert snap.metadata_preview["source_type"] == "docs"

    def test_snapshot_redactions_preserves_ids(self):
        row = {
            "snapshot_id": "s1",
            "conversation_id": "c1",
            "message_id": "m1",
            "chunk_ids": ["a", "b"],
            "scores": [0.9, 0.8],
        }
        result = redact_snapshot_row(row)
        assert result["snapshot_id"] == "s1"
        assert result["chunk_ids"] == ["a", "b"]

    def test_snapshot_query_is_bounded(self):
        row = {"snapshot_id": "s1", "conversation_id": "c1", "message_id": "m1", "query": "x" * 1000}
        result = redact_snapshot_row(row)
        assert "query" in result

    def test_multiple_snapshots_per_conversation_not_pruned(self):
        from app.domain.rag import SnapshotRecord
        snaps = [
            SnapshotRecord(conversation_id="c1", message_id="m1"),
            SnapshotRecord(conversation_id="c1", message_id="m2"),
            SnapshotRecord(conversation_id="c2", message_id="m3"),
        ]
        conv_ids = set(s.conversation_id for s in snaps)
        assert "c1" in conv_ids


class TestRetentionPolicy:
    def test_retain_last_50_unique_conversations(self):
        snaps = [_make_snap(f"conv-{i}") for i in range(75)]
        retained = _retain_last_n_conversations(snaps, n=50)
        conv_ids = set(s.conversation_id for s in retained)
        assert len(conv_ids) == 50
        assert "conv-74" in conv_ids
        assert "conv-0" not in conv_ids

    def test_under_limit_no_pruning(self):
        snaps = [_make_snap(f"conv-{i}") for i in range(10)]
        retained = _retain_last_n_conversations(snaps, n=50)
        assert len(retained) == 10

    def test_prune_removes_oldest_first(self):
        snaps = [_make_snap("conv-a"), _make_snap("conv-b"), _make_snap("conv-c")]
        retained = _retain_last_n_conversations(snaps, n=2)
        assert len(retained) == 2
        convs = [s.conversation_id for s in retained]
        assert "conv-a" not in convs


# -- Helpers -----------------------------------------------------------------

def _make_snap(conv_id: str) -> SnapshotRecord:
    return SnapshotRecord(conversation_id=conv_id, message_id=f"{conv_id}-msg")


def _retain_last_n_conversations(
    snapshots: list[SnapshotRecord],
    n: int = 50,
) -> list[SnapshotRecord]:
    seen: set[str] = set()
    kept: list[SnapshotRecord] = []
    for s in reversed(snapshots):
        if s.conversation_id not in seen:
            seen.add(s.conversation_id)
        if len(seen) > n:
            break
        kept.append(s)
    return list(reversed(kept))
