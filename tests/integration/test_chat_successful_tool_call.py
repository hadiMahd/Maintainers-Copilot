"""Integration tests for successful Phase 7 tool-backed chat flows."""

from __future__ import annotations

import pytest

from app.domain.chat import ChatLimits, ChatRequest
from app.domain.chat_tools import (
    LLMCompletion,
    LLMToolCall,
    RAGRetrievedChunk,
    RAGToolClientResponse,
    ToolSourceReference,
)
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
    def __init__(self) -> None:
        self.store = {}

    async def read(self, user_id: str, conversation_id: str):
        return self.store.get((user_id, conversation_id))

    async def write(self, user_id: str, conversation_id: str, messages, ttl_seconds: int):
        from app.domain.chat import ConversationState

        state = ConversationState(
            user_id=user_id, conversation_id=conversation_id, messages=messages
        )
        self.store[(user_id, conversation_id)] = state
        return state


class _FakeSnapshotService:
    async def store_snapshot(self, **kwargs):
        from app.domain.rag import SnapshotRecord

        return SnapshotRecord(
            conversation_id=kwargs["conversation_id"],
            message_id=kwargs["message_id"],
            trace_id=kwargs.get("trace_id"),
            query=kwargs["query"],
            chunk_ids=["chunk-1"],
            scores=[0.9],
        )


def _build_chat_service(tool_call: LLMToolCall):
    limits = ChatLimits(
        request_size_limit_bytes=8000,
        context_size_limit_chars=12000,
        max_tool_calls=5,
        recursion_limit=8,
        total_timeout_seconds=60,
        per_tool_timeout_seconds=5,
    )
    state_service = ConversationStateService(
        adapter=_DictConversationAdapter(),
        ttl_seconds=1800,
        context_size_limit_chars=limits.context_size_limit_chars,
    )
    tracing_service = ChatTracingService(FakeTraceAdapter())
    tool_service = ToolExecutionService(
        model_server_tools=FakeModelServerTools(),
        rag_tool_client=FakeRAGToolClient(
            RAGToolClientResponse(
                answer="Grounded answer.",
                supporting_sources=[
                    ToolSourceReference(source_id="chunk-1", source_path="docs/auth.md", score=0.9)
                ],
                limitations=[],
                retrieval_trace_id="rag-trace-1",
                retrieved_chunks=[
                    RAGRetrievedChunk(
                        chunk_id="chunk-1", source_path="docs/auth.md", score=0.9, preview="preview"
                    )
                ],
            )
        ),
        memory_tool_client=FakeMemoryToolClient(),
        rag_snapshot_coordinator=ChatRAGSnapshotCoordinator(_FakeSnapshotService()),
        per_tool_timeout_seconds=5,
    )
    graph_service = ChatbotGraphService(
        llm_adapter=FakeLLMAdapter(
            [
                LLMCompletion(tool_calls=[tool_call]),
                LLMCompletion(message="Here is the safe final answer."),
            ]
        ),
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_call",
    [
        LLMToolCall(name="classify_issue", arguments={"title": "bug"}),
        LLMToolCall(name="extract_entities", arguments={"title": "auth service path"}),
        LLMToolCall(name="summarize_issue", arguments={"title": "summary please"}),
        LLMToolCall(name="answer_project_question", arguments={"question": "where is auth?"}),
        LLMToolCall(
            name="write_memory",
            arguments={"content": "preferred editor is vim", "memory_type": "semantic"},
        ),
    ],
)
async def test_supported_tool_calls_complete_successfully(tool_call):
    service = _build_chat_service(tool_call)
    result = await service.execute_chat(
        user_id="u1",
        body=ChatRequest(
            conversation_id="c1",
            message="Please remember this" if tool_call.name == "write_memory" else "help me",
        ),
        request_id="req-1",
    )
    assert any(event.event_type == "tool_status" for event in result.events)
    assert any(event.event_type == "message_delta" for event in result.events)
    assert result.events[-1].event_type == "done"


class _CountingMemoryToolClient:
    def __init__(self):
        self.calls: list[dict] = []

    async def write_memory(self, user_id, payload, *, request_id=None):
        self.calls.append(
            {"user_id": user_id, "content": payload.content, "request_id": request_id}
        )
        import uuid as _uuid

        return __import__(
            "app.domain.chat_tools", fromlist=["WriteMemoryOutput"]
        ).WriteMemoryOutput(
            memory_id=_uuid.uuid4().hex,
            audit_log_id=_uuid.uuid4().hex,
            redaction_summary="no redaction changes",
        )


@pytest.mark.asyncio
async def test_write_memory_limited_to_one_call_per_request():
    memory_client = _CountingMemoryToolClient()
    tool_call = LLMToolCall(
        name="write_memory",
        arguments={"content": "preferred editor is vim", "memory_type": "semantic", "metadata": {}},
    )
    limits = ChatLimits(
        request_size_limit_bytes=8000,
        context_size_limit_chars=12000,
        max_tool_calls=5,
        recursion_limit=8,
        total_timeout_seconds=60,
        per_tool_timeout_seconds=5,
    )
    state_service = ConversationStateService(
        adapter=_DictConversationAdapter(),
        ttl_seconds=1800,
        context_size_limit_chars=limits.context_size_limit_chars,
    )
    tracing_service = ChatTracingService(FakeTraceAdapter())
    tool_service = ToolExecutionService(
        model_server_tools=FakeModelServerTools(),
        rag_tool_client=FakeRAGToolClient(),
        memory_tool_client=memory_client,
        rag_snapshot_coordinator=ChatRAGSnapshotCoordinator(_FakeSnapshotService()),
        per_tool_timeout_seconds=5,
    )
    graph_service = ChatbotGraphService(
        llm_adapter=FakeLLMAdapter(
            [
                LLMCompletion(tool_calls=[tool_call, tool_call]),
                LLMCompletion(message="Here is the safe final answer."),
            ]
        ),
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
        conversation_state_service=state_service,
        chatbot_graph_service=graph_service,
        tracing_service=tracing_service,
        limits=limits,
    )
    result = await service.execute_chat(
        user_id="u1",
        body=ChatRequest(
            conversation_id="c1",
            message="Please remember this and also remember that",
        ),
        request_id="req-1",
    )
    assert len(memory_client.calls) == 1
    assert memory_client.calls[0]["content"] == "preferred editor is vim"

    tool_statuses = [e for e in result.events if e.event_type == "tool_status"]
    assert len(tool_statuses) == 2
    assert "completed" in tool_statuses[0].content
    assert "failed safely" in tool_statuses[1].content
    assert "one call per request" in tool_statuses[1].content

    assert any(e.event_type == "message_delta" for e in result.events)
    assert result.events[-1].event_type == "done"


@pytest.mark.asyncio
async def test_write_memory_allowed_again_on_next_request():
    memory_client = _CountingMemoryToolClient()
    limits = ChatLimits(
        request_size_limit_bytes=8000,
        context_size_limit_chars=12000,
        max_tool_calls=5,
        recursion_limit=8,
        total_timeout_seconds=60,
        per_tool_timeout_seconds=5,
    )
    state_service = ConversationStateService(
        adapter=_DictConversationAdapter(),
        ttl_seconds=1800,
        context_size_limit_chars=limits.context_size_limit_chars,
    )
    tracing_service = ChatTracingService(FakeTraceAdapter())

    def _build_service():
        tool_svc = ToolExecutionService(
            model_server_tools=FakeModelServerTools(),
            rag_tool_client=FakeRAGToolClient(),
            memory_tool_client=memory_client,
            rag_snapshot_coordinator=ChatRAGSnapshotCoordinator(_FakeSnapshotService()),
            per_tool_timeout_seconds=5,
        )
        graph_svc = ChatbotGraphService(
            llm_adapter=FakeLLMAdapter(
                [
                    LLMCompletion(
                        tool_calls=[
                            LLMToolCall(
                                name="write_memory",
                                arguments={
                                    "content": "X",
                                    "memory_type": "semantic",
                                    "metadata": {},
                                },
                            ),
                        ]
                    ),
                    LLMCompletion(message="Done."),
                ]
            ),
            prompt_registry=PromptRegistry.from_settings(
                __import__("app.core.config", fromlist=["AppSettings"]).AppSettings(
                    vault_addr="http://fake",
                    vault_token="fake-token",
                    environment="test",
                )
            ),
            tool_execution_service=tool_svc,
            tracing_service=tracing_service,
        )
        return ChatbotService(
            conversation_state_service=state_service,
            chatbot_graph_service=graph_svc,
            tracing_service=tracing_service,
            limits=limits,
        )

    svc1 = _build_service()
    r1 = await svc1.execute_chat(
        user_id="u1",
        body=ChatRequest(conversation_id="c1", message="Please remember X"),
        request_id="req-1",
    )
    assert len(memory_client.calls) == 1
    assert r1.events[-1].event_type == "done"

    svc2 = _build_service()
    r2 = await svc2.execute_chat(
        user_id="u1",
        body=ChatRequest(conversation_id="c1", message="Please remember Y"),
        request_id="req-2",
    )
    assert len(memory_client.calls) == 2
    assert r2.events[-1].event_type == "done"
