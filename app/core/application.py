"""Application factory."""

from fastapi import FastAPI

from app.api.error_handlers import register_error_handlers
from app.api.routes import api_router
from app.core.config import AppSettings
from app.core.lifespan import lifespan
from app.core.middleware import RequestIDMiddleware


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = AppSettings()
    app = FastAPI(
        title="Maintainer Copilot",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(RequestIDMiddleware, settings=settings)
    register_error_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
