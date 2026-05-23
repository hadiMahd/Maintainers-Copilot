"""Memory inspector persistence.

Repository layer — owns SQL only.  Does NOT call ``.commit()`` or
``.rollback()``.  Transaction boundaries are owned by services.

Provides inspection-specific list/filter/paginate operations distinct
from the semantic-search methods in ``MemoryRepository``.
"""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.orm_models import LongTermMemory


class MemoryInspectorRepository:
    """Async authorized memory inspection queries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_user(
        self,
        owner_user_id: str,
        memory_type: str | None = None,
        limit: int = 25,
        cursor: str | None = None,
    ) -> Sequence[LongTermMemory]:
        stmt = select(LongTermMemory).where(LongTermMemory.owner_user_id == owner_user_id)
        if memory_type:
            stmt = stmt.where(LongTermMemory.memory_type == memory_type)
        if cursor:
            stmt = stmt.where(LongTermMemory.id > cursor)
        stmt = stmt.order_by(LongTermMemory.created_at.desc()).limit(limit + 1)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_all(
        self,
        memory_type: str | None = None,
        limit: int = 25,
        cursor: str | None = None,
    ) -> Sequence[LongTermMemory]:
        stmt = select(LongTermMemory)
        if memory_type:
            stmt = stmt.where(LongTermMemory.memory_type == memory_type)
        if cursor:
            stmt = stmt.where(LongTermMemory.id > cursor)
        stmt = stmt.order_by(LongTermMemory.created_at.desc()).limit(limit + 1)
        result = await self._session.execute(stmt)
        return result.scalars().all()
