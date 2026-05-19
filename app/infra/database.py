"""Async database client."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.domain.errors import DependencyError
from app.domain.models import ReadinessCheck


async_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_engine(database_url: str) -> AsyncEngine:
    """Create an async SQLAlchemy engine."""
    return create_async_engine(database_url)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory."""
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    if async_session_factory is None:
        raise DependencyError("Database session factory not initialized")
    async with async_session_factory() as session:
        yield session


async def probe_database(engine: AsyncEngine, timeout: float = 3.0) -> ReadinessCheck:
    """Probe the database by executing SELECT 1."""
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")  # type: ignore[arg-type]
        return ReadinessCheck(name="postgres", status="ok")
    except Exception:
        return ReadinessCheck(
            name="postgres",
            status="unavailable",
            message="database connection failed",
        )
