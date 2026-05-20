"""Unit tests for typed tool execution and safe recovery."""

from __future__ import annotations

import asyncio

import pytest

from app.domain.chat_tools import LLMToolCall, MemoryWriteIntent, SummarizeIssueOutput
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


class _BrokenModelServerTools(FakeModelServerTools):
    async def summarize_issue(self, payload, **kwargs):
        _ = (payload, kwargs)
        return {"summary": "x" * 9001, "key_facts": [], "unresolved_questions": []}


class _SlowModelServerTools(FakeModelServerTools):
    async def classify_issue(self, payload, **kwargs):
        _ = (payload, kwargs)
        await asyncio.sleep(1.05)
        return await super().classify_issue(payload, **kwargs)


def _service(model_server_tools=None, memory_tool_client=None):
    return ToolExecutionService(
        model_server_tools=model_server_tools or FakeModelServerTools(),
        rag_tool_client=FakeRAGToolClient(),
        memory_tool_client=memory_tool_client or FakeMemoryToolClient(),
        rag_snapshot_coordinator=ChatRAGSnapshotCoordinator(_FakeSnapshotService()),
        per_tool_timeout_seconds=1,
    )


def test_registered_tool_schemas_cover_all_five_tools():
    service = _service()
    assert {tool.name for tool in service.registered_tools()} == {
        "classify_issue",
        "extract_entities",
        "summarize_issue",
        "answer_project_question",
        "write_memory",
    }


@pytest.mark.asyncio
async def test_unknown_tool_rejected_safely():
    service = _service()
    result = await service.execute(
        tool_call=LLMToolCall(name="unknown_tool", arguments={}),
        user_id="u1",
        conversation_id="c1",
        message_id="m1",
        request_id="req-1",
        trace_id="trace-1",
        memory_intent=MemoryWriteIntent(present=False, evidence="none"),
    )
    assert result.status == "failed"
    assert result.error.code == "unknown_tool"


@pytest.mark.asyncio
async def test_invalid_tool_input_rejected_before_execution():
    service = _service()
    result = await service.execute(
        tool_call=LLMToolCall(name="classify_issue", arguments={}),
        user_id="u1",
        conversation_id="c1",
        message_id="m1",
        request_id="req-1",
        trace_id="trace-1",
        memory_intent=MemoryWriteIntent(present=False, evidence="none"),
    )
    assert result.status == "failed"
    assert result.error.code == "invalid_tool_input"


@pytest.mark.asyncio
async def test_per_tool_timeout_returns_safe_failure():
    service = _service(model_server_tools=_SlowModelServerTools())
    result = await service.execute(
        tool_call=LLMToolCall(name="classify_issue", arguments={"title": "bug"}),
        user_id="u1",
        conversation_id="c1",
        message_id="m1",
        request_id="req-1",
        trace_id="trace-1",
        memory_intent=MemoryWriteIntent(present=False, evidence="none"),
    )
    assert result.status == "failed"
    assert result.error.code == "tool_timeout"


@pytest.mark.asyncio
async def test_oversized_tool_output_returns_safe_failure():
    service = _service(model_server_tools=_BrokenModelServerTools())
    result = await service.execute(
        tool_call=LLMToolCall(name="summarize_issue", arguments={"title": "bug"}),
        user_id="u1",
        conversation_id="c1",
        message_id="m1",
        request_id="req-1",
        trace_id="trace-1",
        memory_intent=MemoryWriteIntent(present=False, evidence="none"),
    )
    assert result.status == "failed"
    assert result.error.code in {"tool_output_too_large", "invalid_tool_output"}
