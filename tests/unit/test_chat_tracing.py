"""Unit tests for chat tracing roots, spans, and failure handling."""

from __future__ import annotations

import pytest

from app.infra.tracing import BaseTraceAdapter, FakeTraceAdapter
from app.services.chat_tracing_service import ChatTracingService


class _BrokenTraceAdapter(BaseTraceAdapter):
    async def start_root(self, name: str, metadata: dict):
        raise RuntimeError("boom")

    async def start_span(self, name: str, metadata: dict, parent):
        raise RuntimeError("boom")

    async def finish(self, handle, status: str, metadata: dict):
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_trace_root_and_spans_have_run_ids():
    service = ChatTracingService(FakeTraceAdapter())
    root = await service.start_chat_trace(
        user_id="u1",
        conversation_id="c1",
        message_id="m1",
        request_id="req-1",
    )
    llm_span = await service.start_llm_span(root, "req-1", {"prompt_version": "v1"})
    tool_span = await service.start_tool_span(root, "req-1", {"tool_name": "classify_issue"})
    rag_span = await service.start_rag_span(root, "req-1", {"tool_name": "answer_project_question"})
    assert root is not None and root.run_id
    assert llm_span is not None and llm_span.parent_run_id == root.run_id
    assert tool_span is not None and tool_span.parent_run_id == root.run_id
    assert rag_span is not None and rag_span.parent_run_id == root.run_id


@pytest.mark.asyncio
async def test_tracing_adapter_failures_are_safe():
    service = ChatTracingService(_BrokenTraceAdapter())
    root = await service.start_chat_trace(
        user_id="u1",
        conversation_id="c1",
        message_id="m1",
        request_id="req-1",
    )
    assert root is None
