"""Safe chat tracing workflows built on the project-owned adapter seam."""

from __future__ import annotations

import structlog

from app.domain.chat import TraceRoot
from app.infra.redaction import redact_trace_metadata
from app.infra.tracing import BaseTraceAdapter, TraceHandle

_log = structlog.get_logger


class ChatTracingService:
    """Create chat trace roots and spans without leaking raw payloads."""

    def __init__(self, adapter: BaseTraceAdapter) -> None:
        self._adapter = adapter

    @property
    def backend_name(self) -> str:
        """Return the configured tracing backend label."""
        return self._adapter.backend_name

    async def start_chat_trace(
        self,
        *,
        user_id: str,
        conversation_id: str,
        message_id: str,
        request_id: str,
    ) -> TraceHandle | None:
        metadata = redact_trace_metadata(
            {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "message_id": message_id,
                "request_id": request_id,
            }
        )
        try:
            handle = await self._adapter.start_root("chat_request", metadata)
            _log().info(
                "chat_trace_started",
                request_id=request_id,
                trace_id=handle.trace_id,
                run_id=handle.run_id,
                tracing_backend=handle.backend,
            )
            return handle
        except Exception:
            _log().warning(
                "chat_trace_start_failed",
                request_id=request_id,
                conversation_id=conversation_id,
            )
            return None

    async def start_llm_span(
        self,
        root: TraceHandle | None,
        request_id: str,
        metadata: dict,
    ) -> TraceHandle | None:
        return await self._start_span("llm_call", root, request_id, metadata)

    async def start_tool_span(
        self,
        root: TraceHandle | None,
        request_id: str,
        metadata: dict,
    ) -> TraceHandle | None:
        return await self._start_span("tool_call", root, request_id, metadata)

    async def start_rag_span(
        self,
        root: TraceHandle | None,
        request_id: str,
        metadata: dict,
    ) -> TraceHandle | None:
        return await self._start_span("rag_retrieval", root, request_id, metadata)

    async def finish(self, handle: TraceHandle | None, status: str, metadata: dict) -> None:
        """Finish a trace root or span safely."""
        if handle is None:
            return
        try:
            await self._adapter.finish(handle, status, redact_trace_metadata(metadata))
        except Exception:
            _log().warning(
                "chat_trace_finish_failed",
                request_id=metadata.get("request_id", "unknown"),
                trace_id=handle.trace_id,
                run_id=handle.run_id,
            )

    @staticmethod
    def to_trace_root(handle: TraceHandle | None) -> TraceRoot | None:
        """Convert an adapter handle into a chat trace root model."""
        if handle is None:
            return None
        return TraceRoot(trace_id=handle.trace_id, run_id=handle.run_id, backend=handle.backend)

    async def _start_span(
        self,
        name: str,
        root: TraceHandle | None,
        request_id: str,
        metadata: dict,
    ) -> TraceHandle | None:
        if root is None:
            return None
        try:
            handle = await self._adapter.start_span(
                name,
                redact_trace_metadata(metadata),
                root,
            )
            _log().info(
                "chat_trace_span_started",
                request_id=request_id,
                trace_id=handle.trace_id,
                run_id=handle.run_id,
                span_name=name,
                parent_run_id=handle.parent_run_id,
            )
            return handle
        except Exception:
            _log().warning(
                "chat_trace_span_start_failed",
                request_id=request_id,
                trace_id=root.trace_id,
                span_name=name,
            )
            return None
