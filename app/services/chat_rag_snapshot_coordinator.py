"""Chat-facing wrapper around the existing RAG snapshot service."""

from __future__ import annotations

from app.domain.chat_tools import RAGToolClientResponse, RetrievedSnapshotReference
from app.domain.rag import RetrievalResult, RetrievalResultSet


class ChatRAGSnapshotCoordinator:
    """Store redacted retrieved-chunk snapshots after successful RAG calls."""

    def __init__(self, snapshot_service) -> None:
        self._snapshot_service = snapshot_service

    async def store_snapshot(
        self,
        *,
        conversation_id: str,
        message_id: str,
        question: str,
        rag_result: RAGToolClientResponse,
        trace_id: str | None,
    ) -> RetrievedSnapshotReference:
        retrieval_set = RetrievalResultSet(
            results=[
                RetrievalResult(
                    rank=index,
                    final_score=chunk.score or 0.0,
                    chunk={
                        "chunk_id": chunk.chunk_id,
                        "parent_id": chunk.chunk_id,
                        "source_type": "docs",
                        "source_path": chunk.source_path,
                        "content": chunk.preview or "",
                        "content_hash": chunk.chunk_id,
                        "token_count": max(len(chunk.preview or ""), 1),
                    },
                    content_preview=chunk.preview or "",
                    retrieval_mode="hybrid",
                )
                for index, chunk in enumerate(rag_result.retrieved_chunks, start=1)
            ],
            retrieval_mode="hybrid",
        )
        stored = await self._snapshot_service.store_snapshot(
            conversation_id=conversation_id,
            message_id=message_id,
            query=question,
            results=retrieval_set,
            trace_id=trace_id,
        )
        return RetrievedSnapshotReference(
            snapshot_id=stored.snapshot_id,
            retrieval_trace_id=rag_result.retrieval_trace_id,
        )
