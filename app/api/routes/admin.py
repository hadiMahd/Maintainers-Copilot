"""Admin routes.

Thin HTTP mapping — no SQLAlchemy, Vault, or Redis access directly.
"""

from fastapi import APIRouter, Depends, Request

from app.api.dependencies.authorization import require_admin
from app.domain.auth import (
    AdminInvitationAccept,
    AdminInvitationCreate,
    AdminInvitationRead,
    AuthContext,
    UserRead,
)

router = APIRouter()


def _get_session_factory(request: Request):
    import app.infra.database as db_mod
    return db_mod.async_session_factory


def _get_admin_service(request: Request):
    from app.repositories.admin_invitation_repository import AdminInvitationRepository
    from app.repositories.audit_log_repository import AuditLogRepository
    from app.repositories.user_repository import UserRepository
    from app.services.admin_invitation_service import AdminInvitationService
    from app.services.audit_service import AuditService

    invitation_svc = AdminInvitationService(
        invitation_repo=AdminInvitationRepository,
        audit_repo=AuditLogRepository,
        user_repo=UserRepository,
        session_factory=_get_session_factory(request),
    )
    audit_svc = AuditService(
        audit_repo=AuditLogRepository,
        session_factory=_get_session_factory(request),
    )
    return invitation_svc, audit_svc


@router.post("/invitations", status_code=201, response_model=AdminInvitationRead)
async def create_invitation(
    body: AdminInvitationCreate,
    request: Request,
    current_user: AuthContext = Depends(require_admin),
) -> AdminInvitationRead:
    invitation_svc, _ = _get_admin_service(request)
    request_id = getattr(request.state, "request_id", None)
    return await invitation_svc.create_invitation(
        invitee_email=body.email,
        created_by_user_id=current_user.user_id,
        request_id=request_id,
    )


@router.post("/invitations/accept", response_model=UserRead)
async def accept_invitation(
    body: AdminInvitationAccept,
    request: Request,
    current_user: AuthContext = Depends(require_admin),
) -> UserRead:
    invitation_svc, _ = _get_admin_service(request)
    request_id = getattr(request.state, "request_id", None)
    return await invitation_svc.accept_invitation(
        token=body.token,
        accepted_by_user_id=current_user.user_id,
        request_id=request_id,
    )


@router.get("/audit-logs")
async def list_audit_logs(
    request: Request,
    current_user: AuthContext = Depends(require_admin),
):
    _, audit_svc = _get_admin_service(request)
    request_id = getattr(request.state, "request_id", None)
    items = await audit_svc.list_audit_logs(request_id=request_id)
    return {"items": [item.model_dump() for item in items]}
