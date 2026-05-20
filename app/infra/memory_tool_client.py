"""Tool client wrapper around the Phase 6 long-term memory service."""

from __future__ import annotations

from app.domain.chat_tools import WriteMemoryInput, WriteMemoryOutput
from app.domain.memory import WriteMemoryRequest


class BaseMemoryToolClient:
    """Abstract write-memory tool seam."""

    async def write_memory(
        self,
        user_id: str,
        payload: WriteMemoryInput,
        *,
        request_id: str | None = None,
    ) -> WriteMemoryOutput:
        raise NotImplementedError


class FakeMemoryToolClient(BaseMemoryToolClient):
    """Deterministic memory-write fake for tests."""

    def __init__(self, result: WriteMemoryOutput | None = None) -> None:
        self._result = result or WriteMemoryOutput(
            memory_id="memory-001",
            audit_log_id="audit-001",
            redaction_summary="no redaction changes",
        )

    async def write_memory(
        self,
        user_id: str,
        payload: WriteMemoryInput,
        *,
        request_id: str | None = None,
    ) -> WriteMemoryOutput:
        _ = (user_id, payload, request_id)
        return self._result


class MemoryToolClient(BaseMemoryToolClient):
    """Adapter that delegates to the explicit Phase 6 long-term memory service."""

    def __init__(self, service) -> None:
        self._service = service

    async def write_memory(
        self,
        user_id: str,
        payload: WriteMemoryInput,
        *,
        request_id: str | None = None,
    ) -> WriteMemoryOutput:
        stored = await self._service.write_memory(
            user_id=user_id,
            data=WriteMemoryRequest(
                content=payload.content,
                memory_type=payload.memory_type,
                metadata=payload.metadata,
            ),
            request_id=request_id,
        )
        return WriteMemoryOutput(
            memory_id=stored.id,
            audit_log_id=stored.audit_log_id,
            redaction_summary="content redacted before persistence when needed",
        )
