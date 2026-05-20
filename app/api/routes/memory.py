"""Memory routes."""

from fastapi import APIRouter, Depends, Request

from app.api.dependencies.auth import get_current_user
from app.domain.auth import AuthContext
from app.domain.memory import ShortTermMemoryRead, ShortTermMemoryWrite

router = APIRouter()


def _get_short_term_memory_service(request: Request):
    from app.core.config import AppSettings
    from app.infra.redis_memory import RedisMemoryAdapter
    from app.services.short_term_memory_service import ShortTermMemoryService

    settings: AppSettings = request.app.state.settings
    adapter = RedisMemoryAdapter(request.app.state.redis)
    return ShortTermMemoryService(
        adapter=adapter,
        ttl_seconds=settings.short_term_memory_ttl_seconds,
    )


@router.put("/short-term", response_model=ShortTermMemoryRead)
async def write_short_term_memory(
    body: ShortTermMemoryWrite,
    request: Request,
    current_user: AuthContext = Depends(get_current_user),
) -> ShortTermMemoryRead:
    svc = _get_short_term_memory_service(request)
    request_id = getattr(request.state, "request_id", None)
    return await svc.write_memory(
        user_id=current_user.user_id,
        data=body,
        request_id=request_id,
    )


@router.get("/short-term", response_model=ShortTermMemoryRead)
async def read_short_term_memory(
    conversation_id: str,
    key: str,
    request: Request,
    current_user: AuthContext = Depends(get_current_user),
) -> ShortTermMemoryRead:
    svc = _get_short_term_memory_service(request)
    request_id = getattr(request.state, "request_id", None)
    return await svc.read_memory(
        user_id=current_user.user_id,
        conversation_id=conversation_id,
        key=key,
        request_id=request_id,
    )
