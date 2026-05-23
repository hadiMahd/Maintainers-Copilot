"""Token session persistence.

Repository layer — owns SQL only.  Does NOT call ``.commit()`` or
``.rollback()``.  Transaction boundaries are owned by services.
"""

from __future__ import annotations

import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.orm_models import TokenSession


class TokenSessionRepository:
    """Async token session persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_id: str,
        refresh_token_hash: str,
        expires_at: datetime.datetime,
    ) -> TokenSession:
        import uuid

        session = TokenSession(
            id=uuid.uuid4().hex,
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            issued_at=datetime.datetime.now(datetime.UTC),
            expires_at=expires_at,
        )
        self._session.add(session)
        return session

    async def get_by_refresh_hash(self, refresh_token_hash: str) -> TokenSession | None:
        result = await self._session.execute(
            select(TokenSession).where(TokenSession.refresh_token_hash == refresh_token_hash)
        )
        return result.scalar_one_or_none()

    async def rotate(
        self,
        session_id: str,
        new_hash: str,
        new_expiry: datetime.datetime,
    ) -> None:
        ts = await self._session.get(TokenSession, session_id)
        if ts:
            ts.rotated_at = datetime.datetime.now(datetime.UTC)
            ts.refresh_token_hash = new_hash
            ts.expires_at = new_expiry

    async def revoke(self, session_id: str) -> None:
        ts = await self._session.get(TokenSession, session_id)
        if ts:
            ts.revoked_at = datetime.datetime.now(datetime.UTC)

    async def mark_replay_detected(self, session_id: str) -> None:
        ts = await self._session.get(TokenSession, session_id)
        if ts:
            ts.reuse_detected_at = datetime.datetime.now(datetime.UTC)
