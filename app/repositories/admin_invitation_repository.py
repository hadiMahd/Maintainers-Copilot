"""Admin invitation persistence.

Repository layer — owns SQL only.  Does NOT call ``.commit()`` or
``.rollback()``.  Transaction boundaries are owned by services.
"""

from __future__ import annotations

import datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.orm_models import AdminInvitation


class AdminInvitationRepository:
    """Async admin invitation persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        invitee_email: str,
        created_by_user_id: str,
        token_hash: str,
        expires_at: datetime.datetime,
    ) -> AdminInvitation:
        import uuid
        invitation = AdminInvitation(
            id=uuid.uuid4().hex,
            invitee_email=invitee_email,
            created_by_user_id=created_by_user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self._session.add(invitation)
        return invitation

    async def get_by_email_and_status(
        self, invitee_email: str, status: str = "pending"
    ) -> AdminInvitation | None:
        result = await self._session.execute(
            select(AdminInvitation).where(
                AdminInvitation.invitee_email == invitee_email,
                AdminInvitation.status == status,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_token_hash(self, token_hash: str) -> AdminInvitation | None:
        result = await self._session.execute(
            select(AdminInvitation).where(
                AdminInvitation.token_hash == token_hash
            )
        )
        return result.scalar_one_or_none()

    async def mark_accepted(
        self, invitation_id: str, accepted_by_user_id: str
    ) -> None:
        inv = await self._session.get(AdminInvitation, invitation_id)
        if inv:
            inv.status = "accepted"
            inv.accepted_at = datetime.datetime.now(datetime.UTC)
            inv.accepted_by_user_id = accepted_by_user_id

    async def mark_revoked(self, invitation_id: str) -> None:
        inv = await self._session.get(AdminInvitation, invitation_id)
        if inv:
            inv.status = "revoked"

    async def list_by_creator(self, created_by_user_id: str) -> Sequence[AdminInvitation]:
        result = await self._session.execute(
            select(AdminInvitation).where(
                AdminInvitation.created_by_user_id == created_by_user_id
            ).order_by(AdminInvitation.created_at.desc())
        )
        return result.scalars().all()
