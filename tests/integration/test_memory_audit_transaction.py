"""Integration tests for long-term memory write + audit transaction behavior."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_mock_repo_cls(method_returns: dict):
    class MockRepo:
        def __init__(self, session):
            self._session = session

    for name, return_value in method_returns.items():
        setattr(MockRepo, name, AsyncMock(return_value=return_value))
    return MockRepo


class FakeEmbeddingClient:
    async def embed(self, text: str) -> list[float]:
        return [0.01, 0.02, 0.03]


class TestMemoryAuditTransaction:
    async def test_redacted_memory_persistence_and_single_audit_write(self):
        from app.domain.memory import WriteMemoryRequest
        from app.services.audit_service import MEMORY_WRITE_ACTION
        from app.services.long_term_memory_service import LongTermMemoryService

        session = AsyncMock()

        @asynccontextmanager
        async def factory():
            yield session

        memory_row = MagicMock(
            id="mem1",
            memory_type="semantic",
            redacted_content="token=[REDACTED]",
            content_hash="hash1",
        )
        audit_row = MagicMock(id="audit1")

        memory_repo_cls = _make_mock_repo_cls({"create": memory_row})
        audit_repo_cls = _make_mock_repo_cls({"create": audit_row})

        service = LongTermMemoryService(
            memory_repo=memory_repo_cls,
            audit_repo=audit_repo_cls,
            embedding_client=FakeEmbeddingClient(),
            session_factory=factory,
        )

        result = await service.write_memory(
            user_id="u1",
            data=WriteMemoryRequest(content="token=shhh", memory_type="semantic"),
        )

        assert result.id == "mem1"
        assert result.audit_log_id == "audit1"
        assert memory_repo_cls.create.await_args.kwargs["redacted_content"] == "token=[REDACTED]"
        assert audit_repo_cls.create.await_count == 1
        assert audit_repo_cls.create.await_args.kwargs["action"] == MEMORY_WRITE_ACTION
        assert session.commit.await_count == 1
        assert session.rollback.await_count == 0

    async def test_audit_failure_prevents_unaudited_persistence(self):
        from app.domain.errors import AuditError
        from app.domain.memory import WriteMemoryRequest
        from app.services.long_term_memory_service import LongTermMemoryService

        session = AsyncMock()

        @asynccontextmanager
        async def factory():
            yield session

        memory_row = MagicMock(
            id="mem1",
            memory_type="semantic",
            redacted_content="token=[REDACTED]",
            content_hash="hash1",
        )
        memory_repo_cls = _make_mock_repo_cls({"create": memory_row})

        class FailingAuditRepo:
            def __init__(self, session):
                self._session = session

            async def create(self, **kwargs):
                raise RuntimeError("audit down")

        service = LongTermMemoryService(
            memory_repo=memory_repo_cls,
            audit_repo=FailingAuditRepo,
            embedding_client=FakeEmbeddingClient(),
            session_factory=factory,
        )

        with pytest.raises(AuditError):
            await service.write_memory(
                user_id="u1",
                data=WriteMemoryRequest(content="token=shhh", memory_type="semantic"),
            )

        assert session.commit.await_count == 0
        assert session.rollback.await_count == 1
