"""Integration tests for cross-conversation recall."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock


class FakeEmbeddingClient:
    async def embed(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


class InMemoryMemoryRepo:
    rows: list = []

    def __init__(self, session):
        self._session = session

    async def create(
        self,
        owner_user_id: str,
        memory_type: str,
        redacted_content: str,
        content_hash: str,
        embedding: list[float],
        source: str,
        created_by_user_id: str,
        extra_data: dict | None = None,
    ):
        row = MagicMock(
            id=f"mem{len(self.rows)+1}",
            owner_user_id=owner_user_id,
            memory_type=memory_type,
            redacted_content=redacted_content,
            content_hash=content_hash,
            embedding=embedding,
            source=source,
            created_by_user_id=created_by_user_id,
            extra_data=extra_data or {},
        )
        self.rows.append(row)
        return row

    async def search_same_user_semantic(self, owner_user_id: str, query_embedding: list[float], limit: int = 5):
        return [row for row in self.rows if row.owner_user_id == owner_user_id][:limit]


class InMemoryAuditRepo:
    rows: list = []

    def __init__(self, session):
        self._session = session

    async def create(self, **kwargs):
        row = MagicMock(id=f"audit{len(self.rows)+1}", **kwargs)
        self.rows.append(row)
        return row


class TestCrossConversationRecall:
    async def test_same_user_recall_across_conversations(self):
        from app.domain.memory import LongTermMemoryRecallRequest, WriteMemoryRequest
        from app.services.long_term_memory_service import LongTermMemoryService

        InMemoryMemoryRepo.rows = []
        InMemoryAuditRepo.rows = []

        @asynccontextmanager
        async def factory():
            yield AsyncMock()

        service = LongTermMemoryService(
            memory_repo=InMemoryMemoryRepo,
            audit_repo=InMemoryAuditRepo,
            embedding_client=FakeEmbeddingClient(),
            session_factory=factory,
        )

        await service.write_memory(
            user_id="u1",
            data=WriteMemoryRequest(content="favorite language=python", memory_type="semantic"),
        )

        result = await service.recall_memory(
            user_id="u1",
            data=LongTermMemoryRecallRequest(query="favorite language", conversation_id="later-c2", limit=5),
        )

        assert len(result.items) == 1
        assert result.items[0].content == "favorite language=python"

    async def test_other_user_cannot_recall_first_user_memory(self):
        from app.domain.memory import LongTermMemoryRecallRequest, WriteMemoryRequest
        from app.services.long_term_memory_service import LongTermMemoryService

        InMemoryMemoryRepo.rows = []
        InMemoryAuditRepo.rows = []

        @asynccontextmanager
        async def factory():
            yield AsyncMock()

        service = LongTermMemoryService(
            memory_repo=InMemoryMemoryRepo,
            audit_repo=InMemoryAuditRepo,
            embedding_client=FakeEmbeddingClient(),
            session_factory=factory,
        )

        await service.write_memory(
            user_id="u1",
            data=WriteMemoryRequest(content="favorite editor=vim", memory_type="semantic"),
        )

        result = await service.recall_memory(
            user_id="u2",
            data=LongTermMemoryRecallRequest(query="favorite editor", conversation_id="later-c2", limit=5),
        )

        assert result.items == []

    async def test_no_recall_from_non_explicit_paths(self):
        from app.domain.memory import LongTermMemoryRecallRequest
        from app.services.long_term_memory_service import LongTermMemoryService

        InMemoryMemoryRepo.rows = []
        InMemoryAuditRepo.rows = []

        @asynccontextmanager
        async def factory():
            yield AsyncMock()

        service = LongTermMemoryService(
            memory_repo=InMemoryMemoryRepo,
            audit_repo=InMemoryAuditRepo,
            embedding_client=FakeEmbeddingClient(),
            session_factory=factory,
        )

        result = await service.recall_memory(
            user_id="u1",
            data=LongTermMemoryRecallRequest(query="anything", conversation_id="later-c2", limit=5),
        )

        assert result.items == []
