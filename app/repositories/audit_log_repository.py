"""Audit log persistence.

Repository layer — owns SQL only.  Does NOT call ``.commit()`` or
``.rollback()``.  Transaction boundaries are owned by services.
"""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.orm_models import AuditLog


class AuditLogRepository:
    """Async audit log persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        action: str,
        actor_user_id: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        extra_data: dict | None = None,
    ) -> AuditLog:
        import uuid

        entry = AuditLog(
            id=uuid.uuid4().hex,
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            extra_data=extra_data,
        )
        self._session.add(entry)
        return entry

    async def list_all(self, limit: int = 100, offset: int = 0) -> Sequence[AuditLog]:
        result = await self._session.execute(
            select(AuditLog).order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)
        )
        return result.scalars().all()
