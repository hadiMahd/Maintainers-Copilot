"""Authentication routes.

Thin HTTP mapping — no SQLAlchemy, Vault, or Redis access directly.
"""

from fastapi import APIRouter, Depends, Request

from app.api.dependencies.auth import get_current_user
from app.core.config import AppSettings
from app.domain.auth import (
    AuthContext,
    RefreshRequest,
    TokenPair,
    UserCreate,
    UserLogin,
    UserRead,
)
from app.infra.password_hasher import PasswordHasher
from app.infra.token_signer import TokenSigner
from app.repositories.token_session_repository import TokenSessionRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService

router = APIRouter()


def _get_auth_service(request: Request):
    from app.core.config import AppSettings
    from app.infra.password_hasher import PasswordHasher
    from app.infra.token_signer import TokenSigner
    from app.repositories.token_session_repository import TokenSessionRepository
    from app.repositories.user_repository import UserRepository

    settings: AppSettings = request.app.state.settings
    signer = TokenSigner(settings)
    hasher = PasswordHasher()
    return AuthService(
        user_repo=UserRepository,
        token_repo=TokenSessionRepository,
        hasher=hasher,
        signer=signer,
        session_factory=_get_session_factory(request),
    )


def _get_session_factory(request: Request):
    from app.infra.database import async_session_factory
    return async_session_factory


@router.post("/register", status_code=201, response_model=UserRead)
async def register(body: UserCreate, request: Request) -> UserRead:
    svc = _get_auth_service(request)
    request_id = getattr(request.state, "request_id", None)
    return await svc.register(body, request_id=request_id)


@router.post("/login", response_model=TokenPair)
async def login(body: UserLogin, request: Request) -> TokenPair:
    svc = _get_auth_service(request)
    request_id = getattr(request.state, "request_id", None)
    return await svc.login(body, request_id=request_id)


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, request: Request) -> TokenPair:
    svc = _get_auth_service(request)
    request_id = getattr(request.state, "request_id", None)
    return await svc.refresh_token(body, request_id=request_id)

