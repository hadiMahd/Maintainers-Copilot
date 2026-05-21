"""Memory inspector routes.

Thin HTTP mapping — no SQLAlchemy, Vault, or Redis access directly.
This router shares the /memory prefix with memory.py:
  - memory.py owns POST /long-term and POST /long-term/recall
  - memory_inspector.py owns GET /long-term (inspection listing)
"""

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies.auth import get_current_user
from app.domain.auth import AuthContext
from app.domain.memory_inspector import MemoryInspectionQuery

router = APIRouter()


def _get_memory_inspector_service(request: Request):
    from app.repositories.memory_inspector_repository import MemoryInspectorRepository
    from app.services.memory_inspector_service import MemoryInspectorService

    import app.infra.database as db_mod

    return MemoryInspectorService(
        memory_inspector_repo=MemoryInspectorRepository,
        session_factory=db_mod.async_session_factory,
    )


@router.get("/long-term")
async def inspect_long_term_memory(
    request: Request,
    owner_user_id: str | None = Query(default=None),
    memory_type: str | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    cursor: str | None = Query(default=None),
    current_user: AuthContext = Depends(get_current_user),
):
    svc = _get_memory_inspector_service(request)
    request_id = getattr(request.state, "request_id", None)
    is_admin = current_user.role == "admin"
    query = MemoryInspectionQuery(
        owner_user_id=owner_user_id,
        memory_type=memory_type,
        limit=limit,
        cursor=cursor,
    )
    result = await svc.inspect_memory(
        query=query,
        current_user_id=current_user.user_id,
        is_admin=is_admin,
        request_id=request_id,
    )
    return result.model_dump(mode="json")
