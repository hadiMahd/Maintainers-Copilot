"""Audit service.

Owns audit constants, safe metadata shaping, and audit log listing.
"""

from __future__ import annotations

import uuid
from typing import Callable

import structlog

from app.domain.audit import AuditLogEntry
from app.infra.redaction import redact_audit_metadata

_log = structlog.get_logger

MEMORY_WRITE_ACTION = "memory.write"
ROLE_CHANGE_ACTION = "role.change"
ADMIN_INVITATION_CREATE_ACTION = "admin_invitation.create"
WIDGET_CONFIG_CREATE_ACTION = "widget_config.create"
WIDGET_CONFIG_UPDATE_ACTION = "widget_config.update"
WIDGET_CONFIG_DELETE_ACTION = "widget_config.delete"
CONVERSATION_DELETE_ACTION = "conversation.delete"


class AuditService:
    """Audit workflow service."""

    def __init__(
        self,
        audit_repo: type,
        session_factory: Callable,
    ) -> None:
        self._audit_repo_cls = audit_repo
        self._session_factory = session_factory

    @staticmethod
    def _trace(request_id: str | None = None) -> dict[str, str]:
        rid = request_id or "unknown"
        tid = uuid.uuid4().hex[:12]
        return {"request_id": rid, "trace_id": tid}

    @staticmethod
    def build_memory_write_metadata(
        memory_type: str,
        content_hash: str,
        redacted_content: str,
        redaction_applied: bool,
        source: str,
    ) -> dict:
        """Build safe metadata for memory.write audit rows.

        Raw content is never included.  Only bounded, redacted-safe fields
        are retained.
        """
        metadata = {
            "memory_type": memory_type,
            "content_hash": content_hash,
            "content_length": len(redacted_content),
            "redaction_applied": redaction_applied,
            "source": source,
        }
        return redact_audit_metadata(metadata)

    async def list_audit_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        request_id: str | None = None,
    ) -> list[AuditLogEntry]:
        t = self._trace(request_id)
        log = _log().bind(**t)
        async with self._session_factory() as session:
            repo = self._audit_repo_cls(session)
            rows = await repo.list_all(limit=limit, offset=offset)
            return [
                AuditLogEntry(
                    id=r.id,
                    actor_user_id=r.actor_user_id,
                    action=r.action,
                    target_type=r.target_type,
                    target_id=r.target_id,
                    timestamp=r.timestamp.isoformat()
                    if hasattr(r.timestamp, "isoformat")
                    else str(r.timestamp),
                    metadata=r.extra_data,
                )
                for r in rows
            ]

    async def log_action(
        self,
        *,
        actor_user_id: str,
        action: str,
        target_type: str,
        target_id: str,
        extra_data: dict | None = None,
        request_id: str | None = None,
    ) -> None:
        t = self._trace(request_id)
        safe_data = redact_audit_metadata(extra_data or {})
        async with self._session_factory() as session:
            repo = self._audit_repo_cls(session)
            await repo.create(
                actor_user_id=actor_user_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                extra_data=safe_data,
            )
            await session.commit()
        _log().info(
            "audit_action_logged",
            action=action,
            target_type=target_type,
            target_id=target_id,
            request_id=request_id,
        )
