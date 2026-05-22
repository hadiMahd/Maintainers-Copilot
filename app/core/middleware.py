"""Request ID middleware."""

import logging
import uuid

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import AppSettings
from app.domain.errors import DomainError
from app.domain.models import ErrorResponse

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that binds a request ID to each request."""

    def __init__(self, app, settings: AppSettings) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        header_name = self.settings.request_id_header
        request_id = request.headers.get(header_name.lower())
        if not request_id:
            request_id = str(uuid.uuid4())

        structlog.contextvars.bind_contextvars(request_id=request_id)
        request.state.request_id = request_id
        request.state.trace_id = None

        try:
            response = await call_next(request)
        except DomainError:
            raise
        except Exception:
            logger.error("Unhandled exception", exc_info=True)
            response = JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    error_code="SERVER_ERROR",
                    message="An unexpected error occurred",
                    request_id=request_id,
                    trace_id=getattr(request.state, "trace_id", None),
                ).model_dump(exclude_none=True),
                headers={header_name: request_id},
            )

        response.headers[header_name] = request_id
        trace_id = getattr(request.state, "trace_id", None)
        if trace_id:
            response.headers["X-Trace-ID"] = trace_id
        structlog.contextvars.clear_contextvars()
        return response
