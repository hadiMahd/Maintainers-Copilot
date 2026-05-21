"""Widget configuration routes.

Thin HTTP mapping — no SQLAlchemy, Vault, or Redis access directly.
"""

from fastapi import APIRouter, Depends, Request

from app.api.dependencies.authorization import require_admin
from app.domain.auth import AuthContext
from app.domain.widget_config import WidgetConfigCreate, WidgetConfigUpdate

router = APIRouter()


def _get_widget_config_service(request: Request):
    from app.repositories.widget_config_repository import WidgetConfigRepository
    from app.services.widget_config_service import WidgetConfigService

    import app.infra.database as db_mod

    return WidgetConfigService(
        widget_config_repo=WidgetConfigRepository,
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
    request_id = getattr(request.state, "request_id", None)
    result = await svc.create_config(
        data=body,
        created_by_user_id=current_user.user_id,
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
    request_id = getattr(request.state, "request_id", None)
    result = await svc.update_config(
        config_id=config_id,
        data=body,
        updated_by_user_id=current_user.user_id,
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
