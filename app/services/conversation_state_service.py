"""User-scoped short-term chat conversation state workflows."""

from __future__ import annotations

import structlog

from app.domain.chat import ConversationMessage, ConversationState
from app.infra.redaction import redact_chat_message

_log = structlog.get_logger


class ConversationStateService:
    """Load, bound, and persist short-term chat conversation state."""

    def __init__(self, adapter, ttl_seconds: int, context_size_limit_chars: int) -> None:
        self._adapter = adapter
        self._ttl_seconds = ttl_seconds
        self._context_size_limit_chars = context_size_limit_chars

    async def read_conversation(
        self,
        *,
        user_id: str,
        conversation_id: str,
        request_id: str,
    ) -> ConversationState:
        """Load existing conversation state or degrade safely when Redis is unavailable."""
        try:
            stored = await self._adapter.read(user_id, conversation_id)
            if stored is None:
                return ConversationState(user_id=user_id, conversation_id=conversation_id)
            _log().info(
                "chat_conversation_state_loaded",
                request_id=request_id,
                conversation_id=conversation_id,
                user_id=user_id,
                message_count=len(stored.messages),
            )
            return stored
        except Exception:
            _log().warning(
                "chat_conversation_state_unavailable",
                request_id=request_id,
                conversation_id=conversation_id,
                user_id=user_id,
            )
            return ConversationState(
                user_id=user_id,
                conversation_id=conversation_id,
                degraded=True,
            )

    def shape_context(
        self,
        *,
        state: ConversationState,
        latest_user_message: str,
    ) -> tuple[list[ConversationMessage], bool]:
        """Bound context before the LLM sees it."""
        messages = list(state.messages)
        messages.append(ConversationMessage(role="user", content=latest_user_message))
        trimmed = False
        while self._combined_size(messages) > self._context_size_limit_chars and len(messages) > 1:
            messages.pop(0)
            trimmed = True
        return messages, trimmed

    async def append_exchange(
        self,
        *,
        user_id: str,
        conversation_id: str,
        user_message: str,
        assistant_message: str,
        prior_state: ConversationState,
        request_id: str,
    ) -> ConversationState:
        """Persist the latest user/assistant exchange when Redis is available."""
        if prior_state.degraded:
            return prior_state
        messages = list(prior_state.messages)
        messages.append(ConversationMessage(role="user", content=redact_chat_message(user_message)))
        messages.append(
            ConversationMessage(role="assistant", content=redact_chat_message(assistant_message))
        )
        while self._combined_size(messages) > self._context_size_limit_chars and len(messages) > 2:
            messages.pop(0)
        stored = await self._adapter.write(
            user_id=user_id,
            conversation_id=conversation_id,
            messages=messages,
            ttl_seconds=self._ttl_seconds,
        )
        _log().info(
            "chat_conversation_state_written",
            request_id=request_id,
            conversation_id=conversation_id,
            user_id=user_id,
            message_count=len(stored.messages),
            ttl_seconds=self._ttl_seconds,
        )
        return stored

    @staticmethod
    def _combined_size(messages: list[ConversationMessage]) -> int:
        return sum(len(message.content) for message in messages)
