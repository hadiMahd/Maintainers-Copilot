"""Unit tests for untrusted RAG context handling."""

from __future__ import annotations

import pytest

from app.domain.chat import ChatLimits, ConversationMessage
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
from app.services.tool_execution_service import ToolExecutionService


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


@pytest.mark.asyncio
async def test_rag_tool_results_are_wrapped_as_untrusted_context():
    tracing_service = ChatTracingService(FakeTraceAdapter())
    tool_service = ToolExecutionService(
        model_server_tools=FakeModelServerTools(),
        rag_tool_client=FakeRAGToolClient(
            RAGToolClientResponse(
                answer="Use the auth service.",
                supporting_sources=[
                    ToolSourceReference(source_id="chunk-1", source_path="docs/auth.md", score=0.9)
                ],
                limitations=[],
                retrieval_trace_id="rag-trace-1",
                retrieved_chunks=[
                    RAGRetrievedChunk(
                        chunk_id="chunk-1",
                        source_path="docs/auth.md",
                        score=0.9,
                        preview="raw chunk",
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
                LLMCompletion(
                    tool_calls=[
                        LLMToolCall(
                            name="answer_project_question", arguments={"question": "where is auth?"}
                        )
                    ]
                ),
                LLMCompletion(message="The auth service handles that."),
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
    handle = await tracing_service.start_chat_trace(
        user_id="u1",
        conversation_id="c1",
        message_id="m1",
        request_id="req-1",
    )
    root = tracing_service.to_trace_root(handle)
    result = await graph_service.run(
        request_id="req-1",
        user_id="u1",
        conversation_id="c1",
        message_id="m1",
        user_message="where is auth?",
        context_messages=[ConversationMessage(role="user", content="where is auth?")],
        limits=ChatLimits(
            request_size_limit_bytes=8000,
            context_size_limit_chars=12000,
            max_tool_calls=5,
            recursion_limit=8,
            total_timeout_seconds=60,
            per_tool_timeout_seconds=5,
        ),
        trace_handle=handle,
        trace_root=root,
    )
    tool_messages = [message for message in result.messages if message.role == "tool"]
    assert tool_messages
    assert "untrusted evidence" in tool_messages[0].content.lower()
