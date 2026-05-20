"""Audit log persistence (stub for US2/US4)."""

from sqlalchemy.ext.asyncio import AsyncSession


class AuditLogRepository:
    """Stub for US2/US4.  No business logic until audit workflows are implemented."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
