"""Tool client wrapper around the Phase 6 long-term memory service."""

from __future__ import annotations

from app.domain.chat_tools import (
    RecalledMemoryItem,
    RecallMemoryInput,
    RecallMemoryOutput,
    WriteMemoryInput,
    WriteMemoryOutput,
)
from app.domain.memory import LongTermMemoryRecallRequest, WriteMemoryRequest


class BaseMemoryToolClient:
    """Abstract long-term memory tool seam."""

    async def recall_memory(
        self,
        user_id: str,
        conversation_id: str,
        payload: RecallMemoryInput,
        *,
        request_id: str | None = None,
    ) -> RecallMemoryOutput:
        raise NotImplementedError

    async def write_memory(
        self,
        user_id: str,
        payload: WriteMemoryInput,
        *,
        request_id: str | None = None,
    ) -> WriteMemoryOutput:
        raise NotImplementedError


class FakeMemoryToolClient(BaseMemoryToolClient):
    """Deterministic memory fake for tests."""

    def __init__(
        self,
        result: WriteMemoryOutput | None = None,
        recall_result: RecallMemoryOutput | None = None,
    ) -> None:
        self._result = result or WriteMemoryOutput(
            memory_id="memory-001",
            audit_log_id="audit-001",
            redaction_summary="no redaction changes",
        )
        self._recall_result = recall_result or RecallMemoryOutput(items=[])

    async def recall_memory(
        self,
        user_id: str,
        conversation_id: str,
        payload: RecallMemoryInput,
        *,
        request_id: str | None = None,
    ) -> RecallMemoryOutput:
        _ = (user_id, conversation_id, payload, request_id)
        return self._recall_result

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

    async def recall_memory(
        self,
        user_id: str,
        conversation_id: str,
        payload: RecallMemoryInput,
        *,
        request_id: str | None = None,
    ) -> RecallMemoryOutput:
        recalled = await self._service.recall_memory(
            user_id=user_id,
            data=LongTermMemoryRecallRequest(
                query=payload.query,
                conversation_id=conversation_id,
                limit=payload.limit,
            ),
            request_id=request_id,
        )
        return RecallMemoryOutput(
            items=[
                RecalledMemoryItem(
                    id=item.id,
                    memory_type=item.memory_type,
                    content=item.content,
                    audit_log_id=item.audit_log_id,
                )
                for item in recalled.items
            ]
        )

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
