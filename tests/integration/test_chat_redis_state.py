"""Integration tests for chat short-term state behavior."""

from __future__ import annotations

import pytest

from app.domain.chat import ChatGraphState, ChatLimits, ChatRequest, ConversationState
from app.services.chatbot_service import ChatbotService
from app.services.conversation_state_service import ConversationStateService
from app.services.chat_tracing_service import ChatTracingService
from app.infra.tracing import FakeTraceAdapter


class _DictConversationAdapter:
    def __init__(self, fail: bool = False) -> None:
        self.store = {}
        self.fail = fail

    async def read(self, user_id: str, conversation_id: str):
        if self.fail:
            raise RuntimeError("redis unavailable")
        return self.store.get((user_id, conversation_id))

    async def write(self, user_id: str, conversation_id: str, messages, ttl_seconds: int):
        if self.fail:
            raise RuntimeError("redis unavailable")
        state = ConversationState(user_id=user_id, conversation_id=conversation_id, messages=messages)
        self.store[(user_id, conversation_id)] = state
        return state


class _FakeGraphService:
    async def run(self, **kwargs):
        limits = kwargs["limits"]
        return ChatGraphState(
            request_id=kwargs["request_id"],
            user_id=kwargs["user_id"],
            conversation_id=kwargs["conversation_id"],
            message_id=kwargs["message_id"],
            pending_user_message=kwargs["user_message"],
            messages=kwargs["context_messages"],
            limits=limits,
            trace_id=kwargs["trace_root"].trace_id if kwargs["trace_root"] else None,
            run_id=kwargs["trace_root"].run_id if kwargs["trace_root"] else None,
            final_response="safe answer",
            warnings=kwargs.get("warnings", []),
        )


def _build_service(adapter):
    limits = ChatLimits(
        request_size_limit_bytes=8000,
        context_size_limit_chars=12000,
        max_tool_calls=5,
        recursion_limit=8,
        total_timeout_seconds=60,
        per_tool_timeout_seconds=5,
    )
    return ChatbotService(
        conversation_state_service=ConversationStateService(adapter=adapter, ttl_seconds=1800, context_size_limit_chars=12000),
        chatbot_graph_service=_FakeGraphService(),
        tracing_service=ChatTracingService(FakeTraceAdapter()),
        limits=limits,
    )


@pytest.mark.asyncio
async def test_same_user_conversation_state_is_persisted_and_scoped():
    adapter = _DictConversationAdapter()
    service = _build_service(adapter)
    await service.execute_chat(user_id="u1", body=ChatRequest(conversation_id="c1", message="hello"), request_id="req-1")
    await service.execute_chat(user_id="u1", body=ChatRequest(conversation_id="c1", message="follow up"), request_id="req-2")
    assert adapter.store[("u1", "c1")].messages
    assert ("u2", "c1") not in adapter.store


@pytest.mark.asyncio
async def test_redis_unavailable_degrades_without_long_term_write():
    service = _build_service(_DictConversationAdapter(fail=True))
    result = await service.execute_chat(
        user_id="u1",
        body=ChatRequest(conversation_id="c1", message="hello"),
        request_id="req-1",
    )
    warning_events = [event for event in result.events if event.event_type == "warning"]
    assert warning_events
    assert "unavailable" in warning_events[0].content.lower()
