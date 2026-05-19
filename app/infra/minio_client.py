"""MinIO client placeholder."""

import httpx
import minio

from app.domain.models import ReadinessCheck


def create_minio_client(endpoint: str, access_key: str, secret_key: str) -> minio.Minio:
    """Create a MinIO client."""
    return minio.Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=False,
    )


async def probe_minio(endpoint: str, timeout: float = 3.0) -> ReadinessCheck:
    """Probe MinIO by calling the live health endpoint."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"http://{endpoint}/minio/health/live")
        if response.status_code == 200:
            return ReadinessCheck(name="minio", status="ok")
        return ReadinessCheck(
            name="minio",
            status="unavailable",
            message="minio health check returned non-200",
        )
    except Exception:
        return ReadinessCheck(
            name="minio",
            status="unavailable",
            message="minio health check failed",
        )
