"""User persistence.

Repository layer — owns SQL only.  Does NOT call ``.commit()`` or
``.rollback()``.  Transaction boundaries are owned by services.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.errors import EmailAlreadyRegisteredError
from app.infra.orm_models import User


class UserRepository:
    """Async user persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, email: str, hashed_password: str, role: str = "user") -> User:
        import uuid

        existing = await self.get_by_email(email)
        if existing:
            raise EmailAlreadyRegisteredError(f"Email {email} already registered")

        user = User(
            id=uuid.uuid4().hex,
            email=email,
            hashed_password=hashed_password,
            role=role,
        )
        self._session.add(user)
        return user

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: str) -> User | None:
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_role(self, role: str, limit: int = 1) -> list[User]:
        result = await self._session.execute(select(User).where(User.role == role).limit(limit))
        return list(result.scalars().all())

    async def update_role(self, user_id: str, role: str) -> None:
        user = await self.get_by_id(user_id)
        if user:
            user.role = role
