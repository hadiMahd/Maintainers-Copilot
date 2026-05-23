"""Unit tests for long-term memory service."""

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
    def __init__(self, vector: list[float] | None = None) -> None:
        self.vector = vector or [0.1, 0.2, 0.3]
        self.calls: list[str] = []

    async def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        return self.vector


@pytest.fixture
def mock_session_factory():
    @asynccontextmanager
    async def factory():
        session = AsyncMock()
        yield session

    return factory


@pytest.fixture
def long_term_service(mock_session_factory):
    from app.services.long_term_memory_service import LongTermMemoryService

    memory_row = MagicMock(
        id="mem1",
        memory_type="semantic",
        redacted_content="password=[REDACTED]",
        content_hash="hash1",
    )
    audit_row = MagicMock(id="audit1")

    memory_repo_cls = _make_mock_repo_cls({"create": memory_row})
    audit_repo_cls = _make_mock_repo_cls({"create": audit_row})
    embedding_client = FakeEmbeddingClient()
    service = LongTermMemoryService(
        memory_repo=memory_repo_cls,
        audit_repo=audit_repo_cls,
        embedding_client=embedding_client,
        session_factory=mock_session_factory,
    )
    return service, memory_repo_cls, audit_repo_cls, embedding_client


class TestLongTermMemoryService:
    async def test_explicit_write_memory_persists_redacted_semantic_memory(self, long_term_service):
        from app.domain.memory import WriteMemoryRequest

        service, memory_repo_cls, audit_repo_cls, embedding_client = long_term_service

        result = await service.write_memory(
            user_id="u1",
            data=WriteMemoryRequest(
                content="password=supersecret",
                memory_type="semantic",
            ),
        )

        assert result.id == "mem1"
        assert result.memory_type == "semantic"
        assert result.audit_log_id == "audit1"
        assert embedding_client.calls == ["password=[REDACTED]"]

        create_kwargs = memory_repo_cls.create.await_args.kwargs
        assert create_kwargs["memory_type"] == "semantic"
        assert create_kwargs["redacted_content"] == "password=[REDACTED]"
        assert "supersecret" not in create_kwargs["redacted_content"]

    async def test_semantic_only_validation_rejects_other_types(self, long_term_service):
        from app.domain.errors import UnsupportedMemoryTypeError
        from app.domain.memory import WriteMemoryRequest

        service, memory_repo_cls, audit_repo_cls, embedding_client = long_term_service

        with pytest.raises(UnsupportedMemoryTypeError):
            await service.write_memory(
                user_id="u1",
                data=WriteMemoryRequest(content="remember this", memory_type="episodic"),
            )

        assert memory_repo_cls.create.await_count == 0
        assert audit_repo_cls.create.await_count == 0
        assert embedding_client.calls == []

    async def test_creates_exactly_one_audit_row(self, long_term_service):
        from app.domain.memory import WriteMemoryRequest
        from app.services.audit_service import MEMORY_WRITE_ACTION

        service, memory_repo_cls, audit_repo_cls, _ = long_term_service

        await service.write_memory(
            user_id="u1",
            data=WriteMemoryRequest(content="safe text", memory_type="semantic"),
        )

        assert audit_repo_cls.create.await_count == 1
        assert audit_repo_cls.create.await_args.kwargs["action"] == MEMORY_WRITE_ACTION

    async def test_no_auto_write_behavior(self, long_term_service):
        service, memory_repo_cls, audit_repo_cls, embedding_client = long_term_service

        assert memory_repo_cls.create.await_count == 0
        assert audit_repo_cls.create.await_count == 0
        assert embedding_client.calls == []

    async def test_embedding_boundary_uses_asyncio_to_thread(self, monkeypatch):
        import asyncio

        from app.infra.memory_embedding_client import MemoryEmbeddingClient

        called: dict[str, bool] = {"value": False}

        async def fake_to_thread(func, *args, **kwargs):
            called["value"] = True
            return func(*args, **kwargs)

        monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

        client = MemoryEmbeddingClient(vector_size=8)
        vector = await client.embed("semantic memory text")

        assert len(vector) == 8
        assert called["value"] is True

    async def test_audit_write_failure_rolls_back_memory_write(self, mock_session_factory):
        from app.domain.errors import AuditError
        from app.domain.memory import WriteMemoryRequest
        from app.services.long_term_memory_service import LongTermMemoryService

        memory_row = MagicMock(
            id="mem1",
            memory_type="semantic",
            redacted_content="secret=[REDACTED]",
            content_hash="hash1",
        )
        memory_repo_cls = _make_mock_repo_cls({"create": memory_row})

        class FailingAuditRepo:
            def __init__(self, session):
                self._session = session

            async def create(self, **kwargs):
                raise RuntimeError("audit store unavailable")

        service = LongTermMemoryService(
            memory_repo=memory_repo_cls,
            audit_repo=FailingAuditRepo,
            embedding_client=FakeEmbeddingClient(),
            session_factory=mock_session_factory,
        )

        with pytest.raises(AuditError):
            await service.write_memory(
                user_id="u1",
                data=WriteMemoryRequest(content="secret=abc", memory_type="semantic"),
            )
