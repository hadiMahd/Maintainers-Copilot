"""Unit tests for chat-side retrieved chunk snapshots."""

from __future__ import annotations

import pytest

from app.domain.chat_tools import RAGRetrievedChunk, RAGToolClientResponse
from app.services.chat_rag_snapshot_coordinator import ChatRAGSnapshotCoordinator


class _RecordingSnapshotService:
    def __init__(self) -> None:
        self.kwargs = None

    async def store_snapshot(self, **kwargs):
        from app.domain.rag import SnapshotRecord

        self.kwargs = kwargs
        return SnapshotRecord(
            conversation_id=kwargs["conversation_id"],
            message_id=kwargs["message_id"],
            trace_id=kwargs.get("trace_id"),
            query=kwargs["query"],
            chunk_ids=["chunk-1"],
            scores=[0.9],
        )


@pytest.mark.asyncio
async def test_rag_snapshot_coordinator_returns_snapshot_reference():
    snapshot_service = _RecordingSnapshotService()
    coordinator = ChatRAGSnapshotCoordinator(snapshot_service)
    reference = await coordinator.store_snapshot(
        conversation_id="c1",
        message_id="m1",
        question="where is auth?",
        rag_result=RAGToolClientResponse(
            answer="Use auth service.",
            supporting_sources=[],
            limitations=[],
            retrieval_trace_id="rag-trace-1",
            retrieved_chunks=[
                RAGRetrievedChunk(
                    chunk_id="chunk-1", source_path="docs/auth.md", score=0.9, preview="preview"
                )
            ],
        ),
        trace_id="trace-1",
    )
    assert reference.snapshot_id is not None
    assert reference.retrieval_trace_id == "rag-trace-1"
    assert snapshot_service.kwargs["conversation_id"] == "c1"
