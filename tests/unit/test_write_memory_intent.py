"""Unit tests for explicit write-memory intent gating."""

from __future__ import annotations

import pytest

from app.domain.chat_tools import (
    LLMToolCall,
    MemoryWriteIntent,
    RecalledMemoryItem,
    RecallMemoryOutput,
    detect_write_memory_intent,
)
from app.infra.memory_tool_client import FakeMemoryToolClient
from app.infra.model_server_tools import FakeModelServerTools
from app.infra.rag_tool_client import FakeRAGToolClient
from app.services.chat_rag_snapshot_coordinator import ChatRAGSnapshotCoordinator
from app.services.tool_execution_service import ToolExecutionService


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


class _RecordingMemoryToolClient(FakeMemoryToolClient):
    def __init__(self) -> None:
        super().__init__(
            recall_result=RecallMemoryOutput(
                items=[
                    RecalledMemoryItem(
                        id="memory-1",
                        memory_type="semantic",
                        content="User prefers vim.",
                        audit_log_id="audit-1",
                    )
                ]
            )
        )
        self.called = False
        self.recall_called = False

    async def write_memory(self, user_id, payload, *, request_id=None):
        self.called = True
        return await super().write_memory(user_id, payload, request_id=request_id)

    async def recall_memory(self, user_id, conversation_id, payload, *, request_id=None):
        self.recall_called = True
        return await super().recall_memory(
            user_id,
            conversation_id,
            payload,
            request_id=request_id,
        )


def test_detect_write_memory_intent_requires_explicit_language():
    explicit = detect_write_memory_intent("Please remember that my preferred editor is vim")
    ambiguous = detect_write_memory_intent("This might be useful later")
    assert explicit.present is True
    assert ambiguous.present is False


@pytest.mark.asyncio
async def test_write_memory_tool_never_runs_for_ambiguous_intent():
    memory_client = _RecordingMemoryToolClient()
    service = ToolExecutionService(
        model_server_tools=FakeModelServerTools(),
        rag_tool_client=FakeRAGToolClient(),
        memory_tool_client=memory_client,
        rag_snapshot_coordinator=ChatRAGSnapshotCoordinator(_FakeSnapshotService()),
        per_tool_timeout_seconds=5,
    )
    result = await service.execute(
        tool_call=LLMToolCall(
            name="write_memory",
            arguments={"content": "favorite editor is vim", "memory_type": "semantic"},
        ),
        user_id="u1",
        conversation_id="c1",
        message_id="m1",
        request_id="req-1",
        trace_id="trace-1",
        memory_intent=MemoryWriteIntent(present=False, evidence="ambiguous"),
    )
    assert result.status == "failed"
    assert memory_client.called is False


@pytest.mark.asyncio
async def test_recall_memory_tool_does_not_require_write_intent():
    memory_client = _RecordingMemoryToolClient()
    service = ToolExecutionService(
        model_server_tools=FakeModelServerTools(),
        rag_tool_client=FakeRAGToolClient(),
        memory_tool_client=memory_client,
        rag_snapshot_coordinator=ChatRAGSnapshotCoordinator(_FakeSnapshotService()),
        per_tool_timeout_seconds=5,
    )
    result = await service.execute(
        tool_call=LLMToolCall(
            name="recall_memory",
            arguments={"query": "coding editor preference", "limit": 3},
        ),
        user_id="u1",
        conversation_id="c1",
        message_id="m1",
        request_id="req-1",
        trace_id="trace-1",
        memory_intent=MemoryWriteIntent(present=False, evidence="ambiguous"),
    )
    assert result.status == "success"
    assert result.output is not None
    assert result.output["items"][0]["content"] == "User prefers vim."
    assert memory_client.recall_called is True


def test_recall_memory_is_registered_tool():
    service = ToolExecutionService(
        model_server_tools=FakeModelServerTools(),
        rag_tool_client=FakeRAGToolClient(),
        memory_tool_client=FakeMemoryToolClient(),
        rag_snapshot_coordinator=ChatRAGSnapshotCoordinator(_FakeSnapshotService()),
        per_tool_timeout_seconds=5,
    )
    tool_names = {tool.name for tool in service.registered_tools()}
    assert "recall_memory" in tool_names
