"""User routes."""

from fastapi import APIRouter, Depends, Request

from app.api.dependencies.auth import get_current_user
from app.domain.auth import AuthContext, UserRead

router = APIRouter()


@router.get("/users/me", response_model=UserRead)
async def read_current_user(
    request: Request,
    current_user: AuthContext = Depends(get_current_user),
) -> UserRead:
    import app.infra.database as db_mod
    from app.repositories.user_repository import UserRepository
    async with db_mod.async_session_factory() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(current_user.user_id)
        if not user:
            from app.domain.errors import AuthenticationError
            raise AuthenticationError("User not found")
        return UserRead(
            id=user.id,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
        )
