"""Integration tests for Redis-backed short-term memory TTL behavior."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


class FakeRedisClient:
    """Small async Redis fake with controllable time."""

    def __init__(self) -> None:
        self._now = datetime.now(timezone.utc)
        self._store: dict[str, tuple[str, datetime]] = {}

    async def set(self, key: str, value: str, ex: int) -> bool:
        self._store[key] = (value, self._now + timedelta(seconds=ex))
        return True

    async def get(self, key: str) -> str | None:
        item = self._store.get(key)
        if item is None:
            return None
        value, expires_at = item
        if expires_at <= self._now:
            self._store.pop(key, None)
            return None
        return value

    def advance(self, seconds: int) -> None:
        self._now = self._now + timedelta(seconds=seconds)


class TestRedisMemoryTTL:
    async def test_expired_value_not_returned_after_ttl(self):
        from app.domain.memory import ShortTermMemoryWrite
        from app.infra.redis_memory import RedisMemoryAdapter
        from app.services.short_term_memory_service import ShortTermMemoryService

        client = FakeRedisClient()
        adapter = RedisMemoryAdapter(client)
        service = ShortTermMemoryService(adapter=adapter, ttl_seconds=2)

        await service.write_memory(
            user_id="u1",
            data=ShortTermMemoryWrite(
                conversation_id="c1",
                key="summary",
                value="remember this note",
            ),
        )

        before_expiry = await service.read_memory(
            user_id="u1",
            conversation_id="c1",
            key="summary",
        )
        assert before_expiry.value == "remember this note"

        client.advance(3)

        after_expiry = await service.read_memory(
            user_id="u1",
            conversation_id="c1",
            key="summary",
        )
        assert after_expiry.value is None
        assert after_expiry.expires_at is None
