"""Redis-backed adapter for Phase 7 conversation state."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from app.domain.chat import ConversationMessage, ConversationState


class ConversationStateAdapter:
    """Persist bounded chat conversation state in Redis."""

    def __init__(self, client) -> None:
        self._client = client

    @staticmethod
    def _key(user_id: str, conversation_id: str) -> str:
        return f"chat_state:{user_id}:{conversation_id}"

    async def read(self, user_id: str, conversation_id: str) -> ConversationState | None:
        payload = await self._client.get(self._key(user_id, conversation_id))
        if payload is None:
            return None
        data = json.loads(payload)
        return ConversationState(
            user_id=user_id,
            conversation_id=conversation_id,
            messages=[ConversationMessage.model_validate(item) for item in data.get("messages", [])],
            updated_at=data.get("updated_at"),
            expires_at=data.get("expires_at"),
            degraded=False,
        )

    async def write(
        self,
        user_id: str,
        conversation_id: str,
        messages: list[ConversationMessage],
        ttl_seconds: int,
    ) -> ConversationState:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        state = ConversationState(
            user_id=user_id,
            conversation_id=conversation_id,
            messages=messages,
            expires_at=expires_at.isoformat(),
        )
        await self._client.set(
            self._key(user_id, conversation_id),
            state.model_dump_json(),
            ex=ttl_seconds,
        )
        return state
