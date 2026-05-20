"""Global error handlers."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.errors import DomainError
from app.domain.models import ErrorResponse

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""

    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        trace_id = exc.trace_id or getattr(request.state, "trace_id", None)
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error_code=exc.error_code,
                message=exc.message,
                request_id=request_id,
                trace_id=trace_id,
                details=exc.details or None,
            ).model_dump(exclude_none=True),
            headers={
                "X-Request-ID": request_id,
                **({"X-Trace-ID": trace_id} if trace_id else {}),
            },
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        trace_id = getattr(request.state, "trace_id", None)
        logger.error(
            "Unhandled exception",
            exc_info=True,
            extra={"request_id": request_id, "trace_id": trace_id},
        )
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="SERVER_ERROR",
                message="An unexpected error occurred",
                request_id=request_id,
                trace_id=trace_id,
            ).model_dump(exclude_none=True),
            headers={
                "X-Request-ID": request_id,
                **({"X-Trace-ID": trace_id} if trace_id else {}),
            },
        )
