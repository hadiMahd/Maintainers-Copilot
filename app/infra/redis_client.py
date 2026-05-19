"""Async Redis client."""

import redis.asyncio as redis
from fastapi import Request

from app.domain.errors import DependencyError
from app.domain.models import ReadinessCheck


async def create_redis_client(redis_url: str) -> redis.Redis:
    """Create an async Redis client."""
    return redis.from_url(redis_url, decode_responses=True)


async def get_redis(request: Request) -> redis.Redis:
    """FastAPI dependency that returns the Redis client from app state."""
    client = request.app.state.redis
    if client is None:
        raise DependencyError("Redis client not initialized")
    return client  # type: ignore[return-value]


async def probe_redis(client: redis.Redis, timeout: float = 2.0) -> ReadinessCheck:
    """Probe Redis by sending PING."""
    try:
        pong = await client.ping()
        if pong:
            return ReadinessCheck(name="redis", status="ok")
        return ReadinessCheck(
            name="redis",
            status="unavailable",
            message="redis ping failed",
        )
    except Exception:
        return ReadinessCheck(
            name="redis",
            status="unavailable",
            message="redis connection failed",
        )
