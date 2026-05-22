"""RAG snapshot service — redacted retrieved-chunk snapshot storage with conversation retention."""

from __future__ import annotations

import logging

from app.domain.rag import RetrievalResultSet, SnapshotRecord
from app.infra.redaction import redact_snapshot_row
from app.repositories.rag_snapshot_repository import RAGSnapshotRepository

logger = logging.getLogger(__name__)


class RAGSnapshotService:
    """Store redacted retrieved-chunk snapshots with last-N conversation retention."""

    def __init__(
        self,
        repo: RAGSnapshotRepository,
        *,
        max_conversations: int = 50,
    ) -> None:
        self._repo = repo
        self._max_conversations = max_conversations

    async def store_snapshot(
        self,
        *,
        conversation_id: str,
        message_id: str,
        query: str,
        results: RetrievalResultSet,
        trace_id: str | None = None,
    ) -> SnapshotRecord:
        snap = SnapshotRecord(
            conversation_id=conversation_id,
            message_id=message_id,
            trace_id=trace_id,
            query=query,
            chunk_ids=[r.chunk.chunk_id for r in results.results],
            scores=[r.final_score for r in results.results],
            metadata_preview={
                "retrieval_mode": results.retrieval_mode,
                "result_count": len(results.results),
            },
        )
        redacted = redact_snapshot_row(snap.model_dump())
        await self._repo.insert_snapshot(redacted)
        await self._repo.prune_oldest(self._max_conversations)
        logger.info(
            "Snapshot stored: conv=%s msg=%s chunks=%d",
            conversation_id,
            message_id,
            len(snap.chunk_ids),
        )
        return snap


__all__ = ["RAGSnapshotService"]
