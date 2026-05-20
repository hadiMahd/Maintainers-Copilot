"""Audit service.

Owns transaction boundaries for audit log listing.
"""

from __future__ import annotations

import uuid
from typing import Callable

import structlog

from app.domain.audit import AuditLogEntry

_log = structlog.get_logger


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
