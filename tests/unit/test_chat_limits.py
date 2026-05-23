"""Unit tests for Phase 7 limits and bounded state behavior."""

from __future__ import annotations

import pytest

from app.domain.chat import ChatLimits, ChatRequest, ConversationMessage, ConversationState
from app.domain.chat_tools import LLMCompletion, LLMToolCall
from app.domain.errors import ContextLimitExceededError, RequestTooLargeError
from app.infra.llm_adapter import FakeLLMAdapter
from app.infra.memory_tool_client import FakeMemoryToolClient
from app.infra.model_server_tools import FakeModelServerTools
from app.infra.prompt_registry import PromptRegistry
from app.infra.rag_tool_client import FakeRAGToolClient
from app.infra.tracing import FakeTraceAdapter
from app.services.chat_rag_snapshot_coordinator import ChatRAGSnapshotCoordinator
from app.services.chat_tracing_service import ChatTracingService
from app.services.chatbot_graph_service import ChatbotGraphService
from app.services.chatbot_service import ChatbotService
from app.services.conversation_state_service import ConversationStateService
from app.services.tool_execution_service import ToolExecutionService


class _DictConversationAdapter:
    def __init__(self, initial_state: ConversationState | None = None, fail: bool = False) -> None:
        self.state = initial_state
        self.fail = fail

    async def read(self, user_id: str, conversation_id: str):
        if self.fail:
            raise RuntimeError("redis unavailable")
        if (
            self.state
            and self.state.user_id == user_id
            and self.state.conversation_id == conversation_id
        ):
            return self.state
        return None

    async def write(self, user_id: str, conversation_id: str, messages, ttl_seconds: int):
        _ = ttl_seconds
        self.state = ConversationState(
            user_id=user_id, conversation_id=conversation_id, messages=messages
        )
        return self.state


class _FakeSnapshotService:
    async def store_snapshot(self, **kwargs):
        from app.domain.rag import SnapshotRecord

        return SnapshotRecord(
            conversation_id=kwargs["conversation_id"],
            message_id=kwargs["message_id"],
            trace_id=kwargs.get("trace_id"),
            query=kwargs["query"],
            chunk_ids=[],
            scores=[],
        )


def _build_chat_service(*, completions, limits, initial_state=None):
    state_service = ConversationStateService(
        adapter=_DictConversationAdapter(initial_state=initial_state),
        ttl_seconds=1800,
        context_size_limit_chars=limits.context_size_limit_chars,
    )
    tracing_service = ChatTracingService(FakeTraceAdapter())
    tool_service = ToolExecutionService(
        model_server_tools=FakeModelServerTools(),
        rag_tool_client=FakeRAGToolClient(),
        memory_tool_client=FakeMemoryToolClient(),
        rag_snapshot_coordinator=ChatRAGSnapshotCoordinator(_FakeSnapshotService()),
        per_tool_timeout_seconds=limits.per_tool_timeout_seconds,
    )
    graph_service = ChatbotGraphService(
        llm_adapter=FakeLLMAdapter(completions),
        prompt_registry=PromptRegistry.from_settings(
            __import__("app.core.config", fromlist=["AppSettings"]).AppSettings(
                vault_addr="http://fake",
                vault_token="fake-token",
                environment="test",
            )
        ),
        tool_execution_service=tool_service,
        tracing_service=tracing_service,
    )
    return ChatbotService(
        conversation_state_service=state_service,
        chatbot_graph_service=graph_service,
        tracing_service=tracing_service,
        limits=limits,
    )


def test_conversation_state_shapes_context_to_limit():
    adapter = _DictConversationAdapter()
    service = ConversationStateService(
        adapter=adapter, ttl_seconds=1800, context_size_limit_chars=12
    )
    state = ConversationState(
        user_id="u1",
        conversation_id="c1",
        messages=[
            ConversationMessage(role="user", content="123456"),
            ConversationMessage(role="assistant", content="abcdef"),
        ],
    )
    messages, trimmed = service.shape_context(state=state, latest_user_message="zzzz")
    assert trimmed is True
    assert [message.content for message in messages] == ["abcdef", "zzzz"]


@pytest.mark.asyncio
async def test_request_size_limit_rejected_before_chat_execution():
    limits = ChatLimits(
        request_size_limit_bytes=20,
        context_size_limit_chars=100,
        max_tool_calls=5,
        recursion_limit=8,
        total_timeout_seconds=60,
        per_tool_timeout_seconds=5,
    )
    service = _build_chat_service(completions=[LLMCompletion(message="ok")], limits=limits)
    with pytest.raises(RequestTooLargeError):
        await service.execute_chat(
            user_id="u1",
            body=ChatRequest(conversation_id="c1", message="x" * 50),
            request_id="req-1",
        )


@pytest.mark.asyncio
async def test_context_limit_exceeded_when_latest_message_too_large():
    limits = ChatLimits(
        request_size_limit_bytes=2000,
        context_size_limit_chars=5,
        max_tool_calls=5,
        recursion_limit=8,
        total_timeout_seconds=60,
        per_tool_timeout_seconds=5,
    )
    service = _build_chat_service(completions=[LLMCompletion(message="ok")], limits=limits)
    with pytest.raises(ContextLimitExceededError):
        await service.execute_chat(
            user_id="u1",
            body=ChatRequest(conversation_id="c1", message="this is too large"),
            request_id="req-1",
        )


@pytest.mark.asyncio
async def test_max_tool_call_limit_returns_error_event():
    limits = ChatLimits(
        request_size_limit_bytes=2000,
        context_size_limit_chars=12000,
        max_tool_calls=1,
        recursion_limit=8,
        total_timeout_seconds=60,
        per_tool_timeout_seconds=5,
    )
    service = _build_chat_service(
        completions=[
            LLMCompletion(
                tool_calls=[LLMToolCall(name="classify_issue", arguments={"title": "bug"})]
            ),
            LLMCompletion(
                tool_calls=[LLMToolCall(name="classify_issue", arguments={"title": "bug"})]
            ),
        ],
        limits=limits,
    )
    result = await service.execute_chat(
        user_id="u1",
        body=ChatRequest(conversation_id="c1", message="classify this"),
        request_id="req-1",
    )
    assert result.events[0].event_type == "error"
    assert result.events[0].error.code == "max_tool_calls_exceeded"
