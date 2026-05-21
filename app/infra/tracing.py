"""Tracing adapter seams for chat roots and spans."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid

from app.core.config import AppSettings


@dataclass
class TraceHandle:
    """One root or span handle returned by the tracing adapter."""

    trace_id: str
    run_id: str
    name: str
    backend: str
    parent_run_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = "running"


class BaseTraceAdapter:
    """Project-owned tracing adapter interface."""

    backend_name = "fake"

    async def start_root(self, name: str, metadata: dict[str, Any]) -> TraceHandle:
        raise NotImplementedError

    async def start_span(
        self,
        name: str,
        metadata: dict[str, Any],
        parent: TraceHandle,
    ) -> TraceHandle:
        raise NotImplementedError

    async def finish(self, handle: TraceHandle, status: str, metadata: dict[str, Any]) -> None:
        raise NotImplementedError


class FakeTraceAdapter(BaseTraceAdapter):
    """In-memory tracing adapter for automated tests."""

    backend_name = "fake"

    def __init__(self) -> None:
        self.roots: list[TraceHandle] = []
        self.spans: list[TraceHandle] = []

    async def start_root(self, name: str, metadata: dict[str, Any]) -> TraceHandle:
        handle = TraceHandle(
            trace_id=uuid.uuid4().hex[:12],
            run_id=uuid.uuid4().hex,
            name=name,
            backend=self.backend_name,
            metadata=dict(metadata),
        )
        self.roots.append(handle)
        return handle

    async def start_span(
        self,
        name: str,
        metadata: dict[str, Any],
        parent: TraceHandle,
    ) -> TraceHandle:
        handle = TraceHandle(
            trace_id=parent.trace_id,
            run_id=uuid.uuid4().hex,
            name=name,
            backend=self.backend_name,
            parent_run_id=parent.run_id,
            metadata=dict(metadata),
        )
        self.spans.append(handle)
        return handle

    async def finish(self, handle: TraceHandle, status: str, metadata: dict[str, Any]) -> None:
        handle.status = status
        handle.metadata.update(metadata)


class LangSmithTraceAdapter(FakeTraceAdapter):
    """LangSmith-shaped tracing seam used when credentials are configured."""

    backend_name = "langsmith"

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "LangSmithTraceAdapter":
        """Construct a LangSmith-compatible adapter from settings.

        This adapter intentionally stays network-free in automated tests and local
        development until a real hosted tracing client is required.
        """
        _ = settings
        return cls()
