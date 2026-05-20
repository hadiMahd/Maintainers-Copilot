"""RAG snapshot repository — skeleton for US4 snapshot storage."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class RAGSnapshotRepository:
    """Async repository for redacted retrieved-chunk snapshots.

    Full methods (insert, prune) are implemented in US4.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session


__all__ = ["RAGSnapshotRepository"]
