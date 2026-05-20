"""Memory routes."""

from fastapi import APIRouter, Depends, Request

from app.api.dependencies.auth import get_current_user
from app.domain.auth import AuthContext
from app.domain.memory import (
    LongTermMemoryRead,
    LongTermMemoryRecallRequest,
    LongTermMemoryRecallResponse,
    ShortTermMemoryRead,
    ShortTermMemoryWrite,
    WriteMemoryRequest,
)

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


def _get_long_term_memory_service(request: Request):
    from app.infra.memory_embedding_client import MemoryEmbeddingClient
    from app.repositories.audit_log_repository import AuditLogRepository
    from app.repositories.memory_repository import MemoryRepository
    from app.services.long_term_memory_service import LongTermMemoryService

    import app.infra.database as db_mod

    embedding_client = MemoryEmbeddingClient()
    return LongTermMemoryService(
        memory_repo=MemoryRepository,
        audit_repo=AuditLogRepository,
        embedding_client=embedding_client,
        session_factory=db_mod.async_session_factory,
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


@router.post("/long-term", status_code=201, response_model=LongTermMemoryRead)
async def write_long_term_memory(
    body: WriteMemoryRequest,
    request: Request,
    current_user: AuthContext = Depends(get_current_user),
) -> LongTermMemoryRead:
    svc = _get_long_term_memory_service(request)
    request_id = getattr(request.state, "request_id", None)
    return await svc.write_memory(
        user_id=current_user.user_id,
        data=body,
        request_id=request_id,
    )


@router.post("/long-term/recall", response_model=LongTermMemoryRecallResponse)
async def recall_long_term_memory(
    body: LongTermMemoryRecallRequest,
    request: Request,
    current_user: AuthContext = Depends(get_current_user),
) -> LongTermMemoryRecallResponse:
    svc = _get_long_term_memory_service(request)
    request_id = getattr(request.state, "request_id", None)
    return await svc.recall_memory(
        user_id=current_user.user_id,
        data=body,
        request_id=request_id,
    )
