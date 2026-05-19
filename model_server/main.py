"""Model server application with FastAPI lifespan for classifier artifact loading."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from model_server.api.classifier import router as classifier_router
from model_server.infra.classifier_loader import ClassifierLoader, ArtifactLoadError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load classifier artifact during startup, clean up during shutdown."""
    artifact_dir = os.environ.get("CLASSIFIER_ARTIFACT_DIR", "artifacts/classifiers/classical")
    model_version = os.environ.get("CLASSIFIER_MODEL_VERSION", None)

    loader = ClassifierLoader(artifact_dir=artifact_dir, model_version=model_version)

    try:
        loader.load()
        logger.info(f"Classifier artifact loaded: version={loader.model_version}")
    except ArtifactLoadError as exc:
        logger.warning(f"Classifier artifact could not be loaded: {exc.message}")
    except Exception as exc:
        logger.warning(f"Unexpected error loading classifier artifact: {exc}")

    app.state.classifier_loader = loader
    yield

    loader.unload()
    logger.info("Model server shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the model server FastAPI application."""
    app = FastAPI(
        title="Maintainer's Copilot Classifier Model Server",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(classifier_router)

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        """Add request ID to request state."""
        request_id = request.headers.get("X-Request-ID", None)
        request.state.request_id = request_id
        response = await call_next(request)
        if request_id:
            response.headers["X-Request-ID"] = request_id
        return response

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        loader: ClassifierLoader | None = getattr(app.state, "classifier_loader", None)
        status = "ok" if loader and loader.is_loaded else "unavailable"
        return {"status": status, "version": "0.1.0"}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)