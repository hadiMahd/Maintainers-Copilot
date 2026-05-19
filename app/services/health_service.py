"""Health service."""

import asyncio

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import AppSettings
from app.domain.models import HealthStatus, ReadinessCheck
from app.infra.database import probe_database
from app.infra.minio_client import probe_minio
from app.infra.redis_client import probe_redis


async def check_liveness(settings: AppSettings) -> HealthStatus:
    """Return liveness status without checking dependencies."""
    return HealthStatus(
        status="ok",
        service=settings.service_name,
        checks=[],
    )


async def probe_pgvector(db_engine: AsyncEngine, timeout: float = 3.0) -> ReadinessCheck:
    """Probe pgvector extension by querying pg_extension."""
    try:
        async with db_engine.connect() as conn:
            result = await conn.execute(
                "SELECT extname FROM pg_extension WHERE extname = 'vector'"  # type: ignore[arg-type]
            )
            row = result.fetchone()
            if row:
                return ReadinessCheck(name="pgvector", status="ok")
            return ReadinessCheck(
                name="pgvector",
                status="unavailable",
                message="pgvector extension not installed",
            )
    except Exception:
        return ReadinessCheck(
            name="pgvector",
            status="unavailable",
            message="pgvector check failed",
        )


async def check_readiness(
    db_engine,
    redis_client,
    minio_endpoint: str,
    vault_client,
    settings: AppSettings,
) -> HealthStatus:
    """Run all dependency readiness probes and aggregate status."""
    probes = [
        probe_database(db_engine, timeout=3.0),
        probe_redis(redis_client, timeout=2.0),
        probe_minio(minio_endpoint, timeout=3.0),
        _probe_vault(vault_client),
        probe_pgvector(db_engine, timeout=3.0),
    ]

    results = await asyncio.gather(*probes, return_exceptions=True)
    checks: list[ReadinessCheck] = []
    all_ok = True

    for result in results:
        if isinstance(result, Exception):
            check = ReadinessCheck(
                name="unknown",
                status="unavailable",
                message="probe failed",
            )
            all_ok = False
        else:
            check = result
            if check.status != "ok":
                all_ok = False
        checks.append(check)

    return HealthStatus(
        status="ok" if all_ok else "unavailable",
        service=settings.service_name,
        checks=checks,
    )


async def _probe_vault(vault_client) -> ReadinessCheck:
    """Probe Vault authentication using asyncio.to_thread."""
    try:
        authenticated = await asyncio.wait_for(
            asyncio.to_thread(vault_client.is_authenticated),
            timeout=2.0,
        )
        if authenticated:
            return ReadinessCheck(name="vault", status="ok")
        return ReadinessCheck(
            name="vault",
            status="unavailable",
            message="not authenticated",
        )
    except Exception:
        return ReadinessCheck(
            name="vault",
            status="unavailable",
            message="vault check failed",
        )
