"""Long-term memory service."""

from __future__ import annotations

import hashlib
import uuid
from typing import Callable

import structlog

from app.domain.errors import AuditError, MemoryError, RedactionError, UnsupportedMemoryTypeError
from app.domain.memory import (
    LongTermMemoryRead,
    LongTermMemoryRecallRequest,
    LongTermMemoryRecallResponse,
    MemoryType,
    WriteMemoryRequest,
)
from app.infra.redaction import redact_long_term_memory_content
from app.services.audit_service import AuditService, MEMORY_WRITE_ACTION

_log = structlog.get_logger


class LongTermMemoryService:
    """Explicit semantic memory write workflow with audit linkage."""

    def __init__(
        self,
        memory_repo: type,
        audit_repo: type,
        embedding_client,
        session_factory: Callable,
    ) -> None:
        self._memory_repo_cls = memory_repo
        self._audit_repo_cls = audit_repo
        self._embedding_client = embedding_client
        self._session_factory = session_factory

    @staticmethod
    def _trace(request_id: str | None = None) -> dict[str, str]:
        rid = request_id or "unknown"
        tid = uuid.uuid4().hex[:12]
        return {"request_id": rid, "trace_id": tid}

    async def write_memory(
        self,
        user_id: str,
        data: WriteMemoryRequest,
        request_id: str | None = None,
    ) -> LongTermMemoryRead:
        t = self._trace(request_id)
        log = _log().bind(**t)

        if data.memory_type != MemoryType.semantic.value:
            raise UnsupportedMemoryTypeError("Only semantic memory is supported")

        redacted_content = redact_long_term_memory_content(data.content)
        if not redacted_content.strip():
            raise RedactionError("Redaction removed all memory content")

        try:
            embedding = await self._embedding_client.embed(redacted_content)
        except Exception as exc:
            log.warning("long_term_memory_embedding_failed", user_id=user_id)
            raise MemoryError("Embedding generation failed") from exc

        content_hash = hashlib.sha256(redacted_content.encode()).hexdigest()
        redaction_applied = redacted_content != data.content

        async with self._session_factory() as session:
            memory_repo = self._memory_repo_cls(session)
            audit_repo = self._audit_repo_cls(session)
            try:
                memory_row = await memory_repo.create(
                    owner_user_id=user_id,
                    memory_type=MemoryType.semantic.value,
                    redacted_content=redacted_content,
                    content_hash=content_hash,
                    embedding=embedding,
                    source="write_memory",
                    created_by_user_id=user_id,
                    extra_data={"redaction_applied": redaction_applied},
                )

                audit_metadata = AuditService.build_memory_write_metadata(
                    memory_type=MemoryType.semantic.value,
                    content_hash=content_hash,
                    redacted_content=redacted_content,
                    redaction_applied=redaction_applied,
                    source="write_memory",
                )
                try:
                    audit_row = await audit_repo.create(
                        action=MEMORY_WRITE_ACTION,
                        actor_user_id=user_id,
                        target_type="long_term_memory",
                        target_id=memory_row.id,
                        extra_data=audit_metadata,
                    )
                except Exception as exc:
                    await session.rollback()
                    log.warning("long_term_memory_audit_failed", user_id=user_id)
                    raise AuditError("Audit write failed") from exc

                memory_row.extra_data = {
                    **(memory_row.extra_data or {}),
                    "audit_log_id": audit_row.id,
                }

                await session.commit()
                log.info(
                    "long_term_memory_written",
                    user_id=user_id,
                    memory_id=memory_row.id,
                    audit_log_id=audit_row.id,
                    memory_type=MemoryType.semantic.value,
                    redaction_applied=redaction_applied,
                )
                return LongTermMemoryRead(
                    id=memory_row.id,
                    memory_type=memory_row.memory_type,
                    content=memory_row.redacted_content,
                    audit_log_id=audit_row.id,
                )
            except AuditError:
                raise
            except Exception as exc:
                await session.rollback()
                log.warning("long_term_memory_write_failed", user_id=user_id)
                raise

    async def recall_memory(
        self,
        user_id: str,
        data: LongTermMemoryRecallRequest,
        request_id: str | None = None,
    ) -> LongTermMemoryRecallResponse:
        t = self._trace(request_id)
        log = _log().bind(**t)

        query_text = redact_long_term_memory_content(data.query)
        try:
            query_embedding = await self._embedding_client.embed(query_text)
        except Exception as exc:
            log.warning("long_term_memory_recall_embedding_failed", user_id=user_id)
            raise MemoryError("Recall embedding generation failed") from exc

        async with self._session_factory() as session:
            memory_repo = self._memory_repo_cls(session)
            try:
                rows = await memory_repo.search_same_user_semantic(
                    owner_user_id=user_id,
                    query_embedding=query_embedding,
                    limit=data.limit,
                )
                items = [
                    LongTermMemoryRead(
                        id=row.id,
                        memory_type=row.memory_type,
                        content=row.redacted_content,
                        audit_log_id=(row.extra_data or {}).get("audit_log_id", ""),
                    )
                    for row in rows
                ]
                log.info(
                    "long_term_memory_recalled",
                    user_id=user_id,
                    conversation_id=data.conversation_id,
                    result_count=len(items),
                )
                return LongTermMemoryRecallResponse(items=items)
            except Exception as exc:
                log.warning(
                    "long_term_memory_recall_failed",
                    user_id=user_id,
                    conversation_id=data.conversation_id,
                )
                raise MemoryError("Recall failed") from exc
