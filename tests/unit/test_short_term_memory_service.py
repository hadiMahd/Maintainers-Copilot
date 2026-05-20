"""Unit tests for short-term memory service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


class FakeRedisMemoryAdapter:
    def __init__(self) -> None:
        self.store: dict[tuple[str, str, str], tuple[str, datetime]] = {}
        self.last_write: dict | None = None

    async def set(
        self,
        user_id: str,
        conversation_id: str,
        key: str,
        value: str,
        ttl_seconds: int,
    ) -> datetime:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        self.store[(user_id, conversation_id, key)] = (value, expires_at)
        self.last_write = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "key": key,
            "value": value,
            "ttl_seconds": ttl_seconds,
            "expires_at": expires_at,
        }
        return expires_at

    async def get(
        self,
        user_id: str,
        conversation_id: str,
        key: str,
    ) -> tuple[str, datetime] | None:
        item = self.store.get((user_id, conversation_id, key))
        if item is None:
            return None
        value, expires_at = item
        if expires_at <= datetime.now(timezone.utc):
            self.store.pop((user_id, conversation_id, key), None)
            return None
        return value, expires_at


@pytest.fixture
def memory_service():
    from app.services.short_term_memory_service import ShortTermMemoryService

    adapter = FakeRedisMemoryAdapter()
    service = ShortTermMemoryService(adapter=adapter, ttl_seconds=30)
    return service, adapter


class TestShortTermMemoryService:
    async def test_write_uses_configured_ttl(self, memory_service):
        from app.domain.memory import ShortTermMemoryWrite

        service, adapter = memory_service
        result = await service.write_memory(
            user_id="u1",
            data=ShortTermMemoryWrite(
                conversation_id="c1",
                key="summary",
                value="hello world",
            ),
        )

        assert adapter.last_write is not None
        assert adapter.last_write["ttl_seconds"] == 30
        assert result.conversation_id == "c1"
        assert result.key == "summary"
        assert result.value == "hello world"
        assert result.expires_at is not None

    async def test_same_user_can_read_written_memory(self, memory_service):
        from app.domain.memory import ShortTermMemoryWrite

        service, _ = memory_service
        await service.write_memory(
            user_id="u1",
            data=ShortTermMemoryWrite(
                conversation_id="c1",
                key="summary",
                value="remember this",
            ),
        )

        result = await service.read_memory(
            user_id="u1",
            conversation_id="c1",
            key="summary",
        )

        assert result.value == "remember this"

    async def test_other_user_cannot_read_same_key(self, memory_service):
        from app.domain.memory import ShortTermMemoryWrite

        service, _ = memory_service
        await service.write_memory(
            user_id="u1",
            data=ShortTermMemoryWrite(
                conversation_id="c1",
                key="summary",
                value="private note",
            ),
        )

        result = await service.read_memory(
            user_id="u2",
            conversation_id="c1",
            key="summary",
        )

        assert result.value is None
        assert result.expires_at is None

    async def test_redaction_happens_before_persistence(self, memory_service):
        from app.domain.memory import ShortTermMemoryWrite

        service, adapter = memory_service
        result = await service.write_memory(
            user_id="u1",
            data=ShortTermMemoryWrite(
                conversation_id="c1",
                key="summary",
                value="password=supersecret token: abc123",
            ),
        )

        assert adapter.last_write is not None
        assert "supersecret" not in adapter.last_write["value"]
        assert "[REDACTED]" in adapter.last_write["value"]
        assert result.value == adapter.last_write["value"]
