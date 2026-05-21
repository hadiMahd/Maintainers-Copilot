"""Widget configuration routes.

Thin HTTP mapping — no SQLAlchemy, Vault, or Redis access directly.
"""

from fastapi import APIRouter, Depends, Request

from app.api.dependencies.authorization import require_admin
from app.domain.auth import AuthContext
from app.domain.widget_config import WidgetConfigCreate, WidgetConfigDelete, WidgetConfigUpdate

router = APIRouter()


def _get_widget_config_service(request: Request):
    from app.repositories.widget_config_repository import WidgetConfigRepository
    from app.services.widget_config_service import WidgetConfigService

    import app.infra.database as db_mod

    return WidgetConfigService(
        widget_config_repo=WidgetConfigRepository,
        session_factory=db_mod.async_session_factory,
    )


def _get_audit_service(request: Request):
    from app.repositories.audit_log_repository import AuditLogRepository
    from app.services.audit_service import AuditService

    import app.infra.database as db_mod

    return AuditService(
        audit_repo=AuditLogRepository,
        session_factory=db_mod.async_session_factory,
    )


@router.get("/")
async def list_widget_configs(
    request: Request,
    current_user: AuthContext = Depends(require_admin),
):
    svc = _get_widget_config_service(request)
    request_id = getattr(request.state, "request_id", None)
    items = await svc.list_configs(request_id=request_id)
    return {"items": [item.model_dump(mode="json") for item in items]}


@router.post("/", status_code=201)
async def create_widget_config(
    body: WidgetConfigCreate,
    request: Request,
    current_user: AuthContext = Depends(require_admin),
):
    svc = _get_widget_config_service(request)
    audit_svc = _get_audit_service(request)
    request_id = getattr(request.state, "request_id", None)
    result = await svc.create_config(
        data=body,
        created_by_user_id=current_user.user_id,
        audit_service=audit_svc,
        request_id=request_id,
    )
    return result.model_dump(mode="json")


@router.patch("/{config_id}")
async def update_widget_config(
    config_id: str,
    body: WidgetConfigUpdate,
    request: Request,
    current_user: AuthContext = Depends(require_admin),
):
    svc = _get_widget_config_service(request)
    audit_svc = _get_audit_service(request)
    request_id = getattr(request.state, "request_id", None)
    result = await svc.update_config(
        config_id=config_id,
        data=body,
        updated_by_user_id=current_user.user_id,
        audit_service=audit_svc,
        request_id=request_id,
    )
    return result.model_dump(mode="json")


@router.get("/{config_id}/embed-snippet")
async def get_embed_snippet(
    config_id: str,
    request: Request,
    current_user: AuthContext = Depends(require_admin),
):
    svc = _get_widget_config_service(request)
    request_id = getattr(request.state, "request_id", None)
    result = await svc.generate_embed_snippet(
        config_id=config_id,
        request_id=request_id,
    )
    return result.model_dump(mode="json")


@router.delete("/{config_id}", status_code=200)
async def delete_widget_config(
    config_id: str,
    request: Request,
    current_user: AuthContext = Depends(require_admin),
):
    from datetime import datetime, timezone

    svc = _get_widget_config_service(request)
    audit_svc = _get_audit_service(request)
    request_id = getattr(request.state, "request_id", None)
    result = await svc.delete_config(
        config_id=config_id,
        deleted_by_user_id=current_user.user_id,
        audit_service=audit_svc,
        request_id=request_id,
    )
    return WidgetConfigDelete(
        id=result.id,
        widget_id=result.widget_id,
        deleted_at=datetime.now(timezone.utc),
    ).model_dump(mode="json")
