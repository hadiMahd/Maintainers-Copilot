"""Authorization dependencies.

Thin FastAPI dependency: ``require_admin`` — checks the current user
has admin role.  Raises ``AuthorizationError`` for non-admin callers.
"""

import uuid

import structlog
from fastapi import Depends, Request

from app.api.dependencies.auth import get_current_user
from app.domain.auth import AuthContext
from app.domain.errors import AuthorizationError

_log = structlog.get_logger


async def require_admin(
    request: Request,
    current_user: AuthContext = Depends(get_current_user),
) -> AuthContext:
    """Require the caller to have the admin role.

    Returns the authenticated user context on success.  Raises
    ``AuthorizationError`` (403) for non-admin callers.
    """
    if current_user.role != "admin":
        rid = getattr(request.state, "request_id", "unknown")
        tid = uuid.uuid4().hex[:12]
        _log().warning(
            "admin_guard_rejected",
            request_id=rid,
            trace_id=tid,
            user_id=current_user.user_id,
        )
        raise AuthorizationError("Admin role required")
    return current_user
