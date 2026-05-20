"""Integration tests for chat trace and structured-log correlation."""

from __future__ import annotations

import pytest

from app.domain.chat import ChatLimits, ChatRequest
from app.domain.chat_tools import LLMCompletion, LLMToolCall
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


class _ListLogger:
    def __init__(self) -> None:
        self.entries = []

    def info(self, event, **kwargs):
        self.entries.append((event, kwargs))

    def warning(self, event, **kwargs):
        self.entries.append((event, kwargs))


class _DictConversationAdapter:
    async def read(self, user_id: str, conversation_id: str):
        return None

    async def write(self, user_id: str, conversation_id: str, messages, ttl_seconds: int):
        from app.domain.chat import ConversationState

        return ConversationState(user_id=user_id, conversation_id=conversation_id, messages=messages)


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


@pytest.mark.asyncio
async def test_trace_run_ids_appear_in_chat_logs(monkeypatch):
    import app.services.chatbot_service as chatbot_mod
    import app.services.chat_tracing_service as tracing_mod

    logger = _ListLogger()
    monkeypatch.setattr(chatbot_mod, "_log", lambda: logger)
    monkeypatch.setattr(tracing_mod, "_log", lambda: logger)

    limits = ChatLimits(
        request_size_limit_bytes=8000,
        context_size_limit_chars=12000,
        max_tool_calls=5,
        recursion_limit=8,
        total_timeout_seconds=60,
        per_tool_timeout_seconds=5,
    )
    tracing_service = ChatTracingService(FakeTraceAdapter())
    tool_service = ToolExecutionService(
        model_server_tools=FakeModelServerTools(),
        rag_tool_client=FakeRAGToolClient(),
        memory_tool_client=FakeMemoryToolClient(),
        rag_snapshot_coordinator=ChatRAGSnapshotCoordinator(_FakeSnapshotService()),
        per_tool_timeout_seconds=5,
    )
    graph_service = ChatbotGraphService(
        llm_adapter=FakeLLMAdapter([
            LLMCompletion(tool_calls=[LLMToolCall(name="classify_issue", arguments={"title": "bug"})]),
            LLMCompletion(message="final answer"),
        ]),
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
    service = ChatbotService(
        conversation_state_service=ConversationStateService(_DictConversationAdapter(), 1800, 12000),
        chatbot_graph_service=graph_service,
        tracing_service=tracing_service,
        limits=limits,
    )
    result = await service.execute_chat(
        user_id="u1",
        body=ChatRequest(conversation_id="c1", message="classify this issue"),
        request_id="req-1",
    )
    run_ids = [entry[1].get("run_id") for entry in logger.entries if entry[1].get("run_id")]
    assert result.run_id in run_ids
