"""Memory inspector service.

Owns authorization boundaries for listing long-term memory records.
Users see only their own records; admins see all records.
Repositories never call ``.commit()``; this service only reads.
"""

from __future__ import annotations

import uuid
from typing import Callable

import structlog

from app.domain.memory_inspector import (
    MemoryInspectionQuery,
    MemoryInspectionResult,
    MemoryRecordRead,
)

_log = structlog.get_logger


class MemoryInspectorService:
    """Authorized memory inspection for internal UI."""

    def __init__(
        self,
        memory_inspector_repo: type,
        session_factory: Callable,
    ) -> None:
        self._repo_cls = memory_inspector_repo
        self._session_factory = session_factory

    @staticmethod
    def _trace(request_id: str | None = None) -> dict[str, str]:
        rid = request_id or "unknown"
        tid = uuid.uuid4().hex[:12]
        return {"request_id": rid, "trace_id": tid}

    async def inspect_memory(
        self,
        query: MemoryInspectionQuery,
        current_user_id: str,
        is_admin: bool,
        request_id: str | None = None,
    ) -> MemoryInspectionResult:
        trace = self._trace(request_id)
        _log().info("memory_inspector.inspect", admin=is_admin, **trace)

        async with self._session_factory() as session:
            repo = self._repo_cls(session)

            if is_admin and query.owner_user_id:
                rows = await repo.list_by_user(
                    owner_user_id=query.owner_user_id,
                    memory_type=query.memory_type,
                    limit=query.limit,
                    cursor=query.cursor,
                )
                scope = "admin"
            elif is_admin:
                rows = await repo.list_all(
                    memory_type=query.memory_type,
                    limit=query.limit,
                    cursor=query.cursor,
                )
                scope = "admin"
            else:
                rows = await repo.list_by_user(
                    owner_user_id=current_user_id,
                    memory_type=query.memory_type,
                    limit=query.limit,
                    cursor=query.cursor,
                )
                scope = "own"

        has_more = len(rows) > query.limit
        if has_more:
            rows = rows[: query.limit]

        items = [
            MemoryRecordRead(
                id=row.id,
                owner_user_id=row.owner_user_id,
                memory_type=row.memory_type,
                redacted_content=row.redacted_content,
                source=row.source,
                created_at=row.created_at,
            )
            for row in rows
        ]
        next_cursor = items[-1].id if has_more else None

        return MemoryInspectionResult(items=items, next_cursor=next_cursor, scope=scope)
