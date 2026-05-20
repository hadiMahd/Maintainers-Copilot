"""Authentication dependencies.

Thin FastAPI dependencies for extracting the current user.
"""

import jwt as _jwt

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import AppSettings
from app.domain.auth import AuthContext
from app.domain.errors import TokenError
from app.infra.token_signer import TokenSigner

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthContext:
    """Extract and validate the current authenticated user from Bearer token."""
    if credentials is None:
        raise TokenError("Authentication required")

    settings: AppSettings = request.app.state.settings
    signer = TokenSigner(settings)

    import jwt as _jwt
    try:
        payload = signer.verify_token(credentials.credentials)
    except _jwt.PyJWTError:
        raise TokenError("Invalid or expired access token")

    user_id = payload.get("sub")
    if not user_id:
        raise TokenError("Token missing subject claim")

    return AuthContext(
        user_id=user_id,
        email=payload.get("email", ""),
        role=payload.get("role", "user"),
    )
