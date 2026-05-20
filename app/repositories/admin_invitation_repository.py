"""Admin invitation persistence (stub for US2)."""

from sqlalchemy.ext.asyncio import AsyncSession


class AdminInvitationRepository:
    """Stub for US2.  No business logic until US2 is implemented."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
