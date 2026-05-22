"""Long-term memory persistence.

Repository layer — owns SQL only.  Does NOT call ``.commit()`` or
``.rollback()``.  Transaction boundaries are owned by services.
"""

from __future__ import annotations

import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.orm_models import LongTermMemory


class MemoryRepository:
    """Async semantic memory persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        owner_user_id: str,
        memory_type: str,
        redacted_content: str,
        content_hash: str,
        embedding: list[float],
        source: str,
        created_by_user_id: str,
        extra_data: dict | None = None,
    ) -> LongTermMemory:
        import uuid

        row = LongTermMemory(
            id=uuid.uuid4().hex,
            owner_user_id=owner_user_id,
            memory_type=memory_type,
            redacted_content=redacted_content,
            content_hash=content_hash,
            embedding=embedding,
            source=source,
            created_by_user_id=created_by_user_id,
            extra_data=extra_data,
        )
        self._session.add(row)
        return row

    async def get_by_id(self, memory_id: str) -> LongTermMemory | None:
        result = await self._session.execute(
            select(LongTermMemory).where(LongTermMemory.id == memory_id)
        )
        return result.scalar_one_or_none()

    async def search_same_user_semantic(
        self,
        owner_user_id: str,
        query_embedding: list[float],
        limit: int = 5,
    ) -> list[LongTermMemory]:
        result = await self._session.execute(
            select(LongTermMemory).where(
                LongTermMemory.owner_user_id == owner_user_id,
                LongTermMemory.memory_type == "semantic",
            )
        )
        rows = list(result.scalars().all())
        rows.sort(key=lambda row: self._cosine_distance(row.embedding, query_embedding))
        return rows[:limit]

    @staticmethod
    def _cosine_distance(left, right: list[float]) -> float:
        if not left or not right:
            return 1.0
        left_list = list(left)
        if len(left_list) != len(right):
            return 1.0
        dot = sum(a * b for a, b in zip(left_list, right))
        left_norm = math.sqrt(sum(a * a for a in left_list))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return 1.0
        cosine_similarity = dot / (left_norm * right_norm)
        return 1.0 - cosine_similarity
