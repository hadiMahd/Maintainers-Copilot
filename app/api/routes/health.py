"""Health check routes."""

from fastapi import APIRouter, Depends, Request

from app.api.dependencies.settings import get_settings
from app.core.config import AppSettings
from app.services.health_service import check_liveness, check_readiness

router = APIRouter(tags=["health"])


@router.get("/live")
async def live(settings: AppSettings = Depends(get_settings)):
    """Liveness check — confirms the process is alive."""
    return await check_liveness(settings)


@router.get("/ready")
async def ready(request: Request, settings: AppSettings = Depends(get_settings)):
    """Readiness check — reports dependency health."""
    db_engine = request.app.state.db_engine
    redis_client = request.app.state.redis
    minio_endpoint = request.app.state.settings.minio_endpoint
    vault_client = request.app.state.vault_client

    status = await check_readiness(
        db_engine, redis_client, minio_endpoint, vault_client, settings
    )
    from starlette.responses import JSONResponse
    from fastapi.encoders import jsonable_encoder

    if status.status == "ok":
        return status
    return JSONResponse(
        status_code=503,
        content=jsonable_encoder(status),
    )
