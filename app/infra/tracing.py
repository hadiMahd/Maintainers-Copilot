"""Tracing adapter seams for chat roots and spans."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.config import AppSettings
from app.domain.errors import ConfigError

logger = logging.getLogger(__name__)


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


class LangSmithTraceAdapter(BaseTraceAdapter):
    """LangSmith tracing adapter used when credentials are configured."""

    backend_name = "langsmith"

    def __init__(self, *, client: object, project_name: str) -> None:
        self._client = client
        self._project_name = project_name

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "LangSmithTraceAdapter":
        """Construct a real LangSmith adapter from Vault-resolved settings."""
        api_key = (
            settings.langchain_api_key.get_secret_value()
            if settings.langchain_api_key is not None
            else None
        )
        if not api_key:
            raise ConfigError("LangSmith tracing backend configured but API key is missing")
        if not settings.langsmith_project:
            raise ConfigError("LangSmith tracing backend configured but project is missing")

        try:
            from langsmith import Client
        except ImportError as exc:
            raise ConfigError("LangSmith tracing requires langsmith dependency") from exc

        client_kwargs: dict[str, str] = {"api_key": api_key}
        if settings.langsmith_endpoint:
            client_kwargs["api_url"] = settings.langsmith_endpoint
        return cls(
            client=Client(**client_kwargs),
            project_name=settings.langsmith_project,
        )

    async def start_root(self, name: str, metadata: dict[str, Any]) -> TraceHandle:
        run_id = uuid.uuid4()
        handle = TraceHandle(
            trace_id=run_id.hex[:12],
            run_id=str(run_id),
            name=name,
            backend=self.backend_name,
            metadata=dict(metadata),
        )
        await asyncio.to_thread(
            self._create_run,
            handle,
            metadata,
            "chain",
            None,
        )
        return handle

    async def start_span(
        self,
        name: str,
        metadata: dict[str, Any],
        parent: TraceHandle,
    ) -> TraceHandle:
        run_id = uuid.uuid4()
        handle = TraceHandle(
            trace_id=parent.trace_id,
            run_id=str(run_id),
            name=name,
            backend=self.backend_name,
            parent_run_id=parent.run_id,
            metadata=dict(metadata),
        )
        await asyncio.to_thread(
            self._create_run,
            handle,
            metadata,
            _run_type_for_name(name),
            parent.run_id,
        )
        return handle

    async def finish(self, handle: TraceHandle, status: str, metadata: dict[str, Any]) -> None:
        handle.status = status
        handle.metadata.update(metadata)
        await asyncio.to_thread(self._finish_run, handle, status, metadata)

    def _create_run(
        self,
        handle: TraceHandle,
        metadata: dict[str, Any],
        run_type: str,
        parent_run_id: str | None,
    ) -> None:
        kwargs: dict[str, Any] = {
            "id": uuid.UUID(handle.run_id),
            "name": handle.name,
            "run_type": run_type,
            "inputs": {"metadata": metadata},
            "project_name": self._project_name,
            "start_time": datetime.now(timezone.utc),
            "extra": {"metadata": metadata, "trace_id": handle.trace_id},
        }
        if parent_run_id:
            kwargs["parent_run_id"] = uuid.UUID(parent_run_id)
        try:
            self._client.create_run(**kwargs)
        except Exception as exc:
            logger.warning("LangSmith create_run failed: %s", exc)
            raise

    def _finish_run(
        self,
        handle: TraceHandle,
        status: str,
        metadata: dict[str, Any],
    ) -> None:
        kwargs: dict[str, Any] = {
            "run_id": uuid.UUID(handle.run_id),
            "end_time": datetime.now(timezone.utc),
            "outputs": {"metadata": metadata, "status": status},
            "extra": {"metadata": handle.metadata, "trace_id": handle.trace_id},
        }
        if status.lower() in {"error", "failed"}:
            kwargs["error"] = metadata.get("error", "trace span failed")
        try:
            self._client.update_run(**kwargs)
        except Exception as exc:
            logger.warning("LangSmith update_run failed: %s", exc)
            raise


def _run_type_for_name(name: str) -> str:
    if "llm" in name:
        return "llm"
    if "tool" in name:
        return "tool"
    if "rag" in name or "retrieval" in name:
        return "retriever"
    return "chain"
