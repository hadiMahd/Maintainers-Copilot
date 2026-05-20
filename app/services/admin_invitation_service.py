"""Admin invitation service.

Owns transaction boundaries for invitation creation, token acceptance,
and role-change audit logging.  Repositories never call ``.commit()``;
this service commits or rolls back once per workflow.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable

import structlog

from app.domain.auth import AdminInvitationCreate, AdminInvitationRead, UserRead
from app.domain.errors import InvitationError

_log = structlog.get_logger


class AdminInvitationService:
    """Admin invitation and role-change workflows."""

    def __init__(
        self,
        invitation_repo: type,
        audit_repo: type,
        user_repo: type,
        session_factory: Callable,
    ) -> None:
        self._invitation_repo_cls = invitation_repo
        self._audit_repo_cls = audit_repo
        self._user_repo_cls = user_repo
        self._session_factory = session_factory

    @staticmethod
    def _trace(request_id: str | None = None) -> dict[str, str]:
        rid = request_id or "unknown"
        tid = uuid.uuid4().hex[:12]
        return {"request_id": rid, "trace_id": tid}

    async def create_invitation(
        self,
        invitee_email: str,
        created_by_user_id: str,
        request_id: str | None = None,
    ) -> AdminInvitationRead:
        t = self._trace(request_id)
        log = _log().bind(**t)
        async with self._session_factory() as session:
            try:
                inv_repo = self._invitation_repo_cls(session)
                existing = await inv_repo.get_by_email_and_status(invitee_email)
                if existing:
                    raise InvitationError("Pending invitation already exists for this email")

                token = secrets.token_urlsafe(48)
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                expires_at = datetime.now(timezone.utc) + timedelta(hours=48)

                invitation = await inv_repo.create(
                    invitee_email, created_by_user_id, token_hash, expires_at,
                )

                audit_repo = self._audit_repo_cls(session)
                await audit_repo.create(
                    action="admin_invitation.create",
                    actor_user_id=created_by_user_id,
                    target_type="admin_invitation",
                    target_id=invitation.id,
                    extra_data={"invitee_email": invitee_email},
                )

                await session.commit()
                log.info("invitation_created", invitation_id=invitation.id)
                return AdminInvitationRead(
                    id=invitation.id,
                    invitee_email=invitation.invitee_email,
                    status=invitation.status,
                    expires_at=invitation.expires_at.isoformat()
                    if isinstance(invitation.expires_at, datetime)
                    else str(invitation.expires_at),
                )
            except InvitationError:
                await session.rollback()
                raise
            except Exception:
                await session.rollback()
                log.warning("invitation_create_rollback")
                raise

    async def accept_invitation(
        self,
        token: str,
        accepted_by_user_id: str,
        request_id: str | None = None,
    ) -> UserRead:
        t = self._trace(request_id)
        log = _log().bind(**t)
        async with self._session_factory() as session:
            try:
                inv_repo = self._invitation_repo_cls(session)
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                invitation = await inv_repo.get_by_token_hash(token_hash)

                if not invitation:
                    raise InvitationError("Invalid invitation token")

                if invitation.status == "accepted":
                    raise InvitationError("Invitation already accepted")
                if invitation.status == "revoked":
                    raise InvitationError("Invitation has been revoked")
                if invitation.status == "expired":
                    raise InvitationError("Invitation has expired")

                now = datetime.now(timezone.utc)
                if invitation.expires_at is not None:
                    expires = (
                        invitation.expires_at
                        if isinstance(invitation.expires_at, datetime)
                        else datetime.fromisoformat(str(invitation.expires_at))
                    )
                    if expires < now:
                        raise InvitationError("Invitation has expired")

                await inv_repo.mark_accepted(invitation.id, accepted_by_user_id)

                user_repo = self._user_repo_cls(session)
                await user_repo.update_role(accepted_by_user_id, "admin")

                audit_repo = self._audit_repo_cls(session)
                await audit_repo.create(
                    action="role.change",
                    actor_user_id=accepted_by_user_id,
                    target_type="user",
                    target_id=accepted_by_user_id,
                    extra_data={
                        "new_role": "admin",
                        "via_invitation_id": invitation.id,
                    },
                )

                await session.commit()
                log.info("invitation_accepted", invitation_id=invitation.id)
                user = await user_repo.get_by_id(accepted_by_user_id)
                return UserRead(
                    id=user.id if user else accepted_by_user_id,
                    email=user.email if user else "",
                    role="admin",
                    is_active=user.is_active if user else True,
                )
            except InvitationError:
                await session.rollback()
                raise
            except Exception:
                await session.rollback()
                log.warning("invitation_accept_rollback")
                raise
