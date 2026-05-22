"""Short-term memory service."""

from __future__ import annotations

import uuid

import structlog

from app.domain.errors import MemoryError
from app.domain.memory import ShortTermMemoryRead, ShortTermMemoryWrite
from app.infra.redaction import redact_short_term_memory_value

_log = structlog.get_logger


class ShortTermMemoryService:
    """Short-term memory workflows with pre-persistence redaction."""

    def __init__(self, adapter, ttl_seconds: int) -> None:
        self._adapter = adapter
        self._ttl_seconds = ttl_seconds

    @staticmethod
    def _trace(request_id: str | None = None) -> dict[str, str]:
        rid = request_id or "unknown"
        tid = uuid.uuid4().hex[:12]
        return {"request_id": rid, "trace_id": tid}

    async def write_memory(
        self,
        user_id: str,
        data: ShortTermMemoryWrite,
        request_id: str | None = None,
    ) -> ShortTermMemoryRead:
        t = self._trace(request_id)
        log = _log().bind(**t)
        try:
            redacted_value = redact_short_term_memory_value(data.value)
            expires_at = await self._adapter.set(
                user_id=user_id,
                conversation_id=data.conversation_id,
                key=data.key,
                value=redacted_value,
                ttl_seconds=self._ttl_seconds,
            )
            log.info(
                "short_term_memory_written",
                user_id=user_id,
                conversation_id=data.conversation_id,
                key=data.key,
                ttl_seconds=self._ttl_seconds,
                redaction_applied=redacted_value != data.value,
            )
            return ShortTermMemoryRead(
                conversation_id=data.conversation_id,
                key=data.key,
                value=redacted_value,
                expires_at=expires_at.isoformat(),
            )
        except Exception as exc:
            log.warning(
                "short_term_memory_write_failed",
                user_id=user_id,
                conversation_id=data.conversation_id,
                key=data.key,
            )
            raise MemoryError("Short-term memory write failed") from exc

    async def read_memory(
        self,
        user_id: str,
        conversation_id: str,
        key: str,
        request_id: str | None = None,
    ) -> ShortTermMemoryRead:
        t = self._trace(request_id)
        log = _log().bind(**t)
        try:
            item = await self._adapter.get(user_id, conversation_id, key)
            if item is None:
                log.info(
                    "short_term_memory_miss",
                    user_id=user_id,
                    conversation_id=conversation_id,
                    key=key,
                )
                return ShortTermMemoryRead(
                    conversation_id=conversation_id,
                    key=key,
                    value=None,
                    expires_at=None,
                )
            value, expires_at = item
            log.info(
                "short_term_memory_read",
                user_id=user_id,
                conversation_id=conversation_id,
                key=key,
            )
            return ShortTermMemoryRead(
                conversation_id=conversation_id,
                key=key,
                value=value,
                expires_at=expires_at.isoformat(),
            )
        except Exception as exc:
            log.warning(
                "short_term_memory_read_failed",
                user_id=user_id,
                conversation_id=conversation_id,
                key=key,
            )
            raise MemoryError("Short-term memory read failed") from exc
