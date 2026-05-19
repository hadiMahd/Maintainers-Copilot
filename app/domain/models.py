"""Domain models."""

from typing import Literal

from pydantic import BaseModel


class RequestContext(BaseModel):
    """Request correlation context."""

    request_id: str
    trace_id: str | None = None
    path: str | None = None
    method: str | None = None


class ReadinessCheck(BaseModel):
    """Readiness check result."""

    name: str
    status: Literal["ok", "degraded", "unavailable"]
    message: str | None = None


class HealthStatus(BaseModel):
    """Health status response."""

    status: Literal["ok", "degraded", "unavailable"]
    service: str
    version: str | None = None
    checks: list[ReadinessCheck] = []
    request_id: str | None = None


class ErrorResponse(BaseModel):
    """Structured error response."""

    error_code: str
    message: str
    request_id: str
