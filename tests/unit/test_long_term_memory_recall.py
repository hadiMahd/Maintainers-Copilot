"""Unit tests for long-term memory recall behavior."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock


def _make_mock_repo_cls(rows: list):
    class MockRepo:
        def __init__(self, session):
            self._session = session

        async def search_same_user_semantic(
            self, owner_user_id: str, query_embedding: list[float], limit: int = 5
        ):
            return [row for row in rows if row.owner_user_id == owner_user_id][:limit]

    return MockRepo


class FakeEmbeddingClient:
    async def embed(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


async def _build_service(rows: list):
    from app.services.long_term_memory_service import LongTermMemoryService

    @asynccontextmanager
    async def factory():
        yield AsyncMock()

    repo_cls = _make_mock_repo_cls(rows)
    return LongTermMemoryService(
        memory_repo=repo_cls,
        audit_repo=MagicMock(),
        embedding_client=FakeEmbeddingClient(),
        session_factory=factory,
    )


class TestLongTermMemoryRecall:
    async def test_same_user_recall_returns_only_same_user_entries(self):
        from app.domain.memory import LongTermMemoryRecallRequest

        row1 = MagicMock(
            id="m1",
            owner_user_id="u1",
            memory_type="semantic",
            redacted_content="favorite color is [REDACTED]",
            extra_data={"audit_log_id": "a1"},
        )
        row2 = MagicMock(
            id="m2",
            owner_user_id="u2",
            memory_type="semantic",
            redacted_content="other user private memory",
            extra_data={"audit_log_id": "a2"},
        )
        service = await _build_service([row1, row2])

        result = await service.recall_memory(
            user_id="u1",
            data=LongTermMemoryRecallRequest(
                query="favorite color", conversation_id="later-c1", limit=5
            ),
        )

        assert len(result.items) == 1
        assert result.items[0].id == "m1"
        assert result.items[0].content == "favorite color is [REDACTED]"

    async def test_cross_user_leakage_prevented(self):
        from app.domain.memory import LongTermMemoryRecallRequest

        row = MagicMock(
            id="m2",
            owner_user_id="u2",
            memory_type="semantic",
            redacted_content="other user private memory",
            extra_data={"audit_log_id": "a2"},
        )
        service = await _build_service([row])

        result = await service.recall_memory(
            user_id="u1",
            data=LongTermMemoryRecallRequest(
                query="private memory", conversation_id="later-c1", limit=5
            ),
        )

        assert result.items == []

    async def test_no_recall_from_normal_requests_that_never_wrote_memory(self):
        from app.domain.memory import LongTermMemoryRecallRequest

        service = await _build_service([])

        result = await service.recall_memory(
            user_id="u1",
            data=LongTermMemoryRecallRequest(query="anything", conversation_id="later-c1", limit=5),
        )

        assert result.items == []
