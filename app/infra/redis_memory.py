"""Redis short-term memory adapter."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone


class RedisMemoryAdapter:
    """Persist short-term memory in Redis with TTL-bound keys."""

    def __init__(self, client) -> None:
        self._client = client

    @staticmethod
    def _key(user_id: str, conversation_id: str, key: str) -> str:
        return f"short_term_memory:{user_id}:{conversation_id}:{key}"

    async def set(
        self,
        user_id: str,
        conversation_id: str,
        key: str,
        value: str,
        ttl_seconds: int,
    ) -> datetime:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        payload = json.dumps(
            {
                "conversation_id": conversation_id,
                "key": key,
                "value": value,
                "expires_at": expires_at.isoformat(),
            }
        )
        await self._client.set(self._key(user_id, conversation_id, key), payload, ex=ttl_seconds)
        return expires_at

    async def get(
        self,
        user_id: str,
        conversation_id: str,
        key: str,
    ) -> tuple[str, datetime] | None:
        payload = await self._client.get(self._key(user_id, conversation_id, key))
        if payload is None:
            return None
        data = json.loads(payload)
        expires_at = datetime.fromisoformat(data["expires_at"])
        return data["value"], expires_at
