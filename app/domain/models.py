"""Domain models."""

from typing import Any, Literal

from pydantic import BaseModel, Field


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
    checks: list[ReadinessCheck] = Field(default_factory=list)
    request_id: str | None = None


class ErrorResponse(BaseModel):
    """Structured error response."""

    error_code: str
    message: str
    request_id: str
    trace_id: str | None = None
    details: dict[str, Any] | None = None
