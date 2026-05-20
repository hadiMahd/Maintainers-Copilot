"""RAG snapshot repository — insert and prune with conversation retention."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class RAGSnapshotRepository:
    """Async repository for redacted retrieved-chunk snapshots."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_snapshot(self, data: dict) -> None:
        await self._session.execute(
            text(
                "INSERT INTO rag_snapshots "
                "(snapshot_id, conversation_id, message_id, trace_id, "
                "query, chunk_ids, scores, metadata_preview) "
                "VALUES (:snapshot_id, :conversation_id, :message_id, :trace_id, "
                ":query, :chunk_ids, :scores, :metadata_preview)"
            ),
            {
                "snapshot_id": data.get("snapshot_id"),
                "conversation_id": data.get("conversation_id"),
                "message_id": data.get("message_id"),
                "trace_id": data.get("trace_id"),
                "query": data.get("query"),
                "chunk_ids": data.get("chunk_ids"),
                "scores": data.get("scores"),
                "metadata_preview": data.get("metadata_preview"),
            },
        )

    async def prune_oldest(self, max_conversations: int) -> None:
        await self._session.execute(
            text(
                "DELETE FROM rag_snapshots WHERE conversation_id IN ("
                "SELECT conversation_id FROM ("
                "SELECT conversation_id, MAX(created_at) AS last_seen "
                "FROM rag_snapshots GROUP BY conversation_id "
                "ORDER BY last_seen DESC "
                "OFFSET :max_conversations"
                ") AS old_convs"
                ")"
            ),
            {"max_conversations": max_conversations},
        )


__all__ = ["RAGSnapshotRepository"]
