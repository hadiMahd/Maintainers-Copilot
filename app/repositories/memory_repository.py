"""Long-term memory persistence (stub for US4)."""

from sqlalchemy.ext.asyncio import AsyncSession


class MemoryRepository:
    """Stub for US4.  No business logic until US4 is implemented."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
