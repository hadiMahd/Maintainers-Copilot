"""Model server application with FastAPI lifespan for classifier, NER, and summarization."""

from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from model_server.api.classifier import router as classifier_router
from model_server.api.issue_analysis import router as issue_analysis_router
from model_server.infra.classifier_loader import ArtifactLoadError, ClassifierLoader
from model_server.infra.entity_ruler_pipeline import EntityRulerPipeline
from model_server.infra.summarization_adapter import (
    AzureOpenAISummarizationAdapter,
    FakeSummarizationAdapter,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    artifact_dir = os.environ.get("CLASSIFIER_ARTIFACT_DIR", "artifacts/classifiers/classical")
    model_version = os.environ.get("CLASSIFIER_MODEL_VERSION", None)

    classifier_loader = ClassifierLoader(artifact_dir=artifact_dir, model_version=model_version)
    try:
        classifier_loader.load()
        logger.info("Classifier artifact loaded: version=%s", classifier_loader.model_version)
    except ArtifactLoadError as exc:
        logger.warning("Classifier artifact could not be loaded: %s", exc.message)
    except Exception as exc:
        logger.warning("Unexpected error loading classifier artifact: %s", exc)

    ner_pipeline = EntityRulerPipeline()
    try:
        ner_pipeline.initialize()
        logger.info("EntityRuler pipeline initialized: types=%s", len(ner_pipeline.supported_entity_types))
    except Exception as exc:
        logger.warning("EntityRuler pipeline initialization failed: %s", exc)
        ner_pipeline._configured = False

    azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    azure_api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    azure_model = os.environ.get("AZURE_OPENAI_MODEL")
    langsmith_enabled = bool(os.environ.get("LANGCHAIN_API_KEY"))

    if azure_endpoint and azure_api_key and azure_model:
        summarization_adapter = AzureOpenAISummarizationAdapter(
            endpoint=azure_endpoint,
            api_key=azure_api_key,
            deployment_name=azure_model,
            timeout_seconds=int(os.environ.get("SUMMARIZATION_TIMEOUT_SECONDS", "15")),
            langsmith_enabled=langsmith_enabled,
        )
        logger.info(
            "Azure OpenAI summarization adapter created: model=%s timeout=%d langsmith=%s",
            azure_model,
            summarization_adapter.timeout_seconds,
            langsmith_enabled,
        )
    else:
        summarization_adapter = FakeSummarizationAdapter(
            timeout_seconds=int(os.environ.get("SUMMARIZATION_TIMEOUT_SECONDS", "15")),
        )
        logger.info("Fake summarization adapter created (no Azure credentials configured)")

    app.state.classifier_loader = classifier_loader
    app.state.ner_pipeline = ner_pipeline
    app.state.summarization_adapter = summarization_adapter

    yield

    classifier_loader.unload()
    logger.info("Model server shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Maintainer's Copilot Classifier Model Server",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(classifier_router)
    app.include_router(issue_analysis_router)

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        request.state.trace_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Trace-ID"] = request.state.trace_id
        return response

    @app.get("/health")
    async def health():
        loader: ClassifierLoader | None = getattr(app.state, "classifier_loader", None)
        ner_ok = getattr(getattr(app.state, "ner_pipeline", None), "configured", False)
        summ = getattr(app.state, "summarization_adapter", None)
        status = "ok" if loader and loader.is_loaded else "unavailable"
        return {
            "status": status,
            "version": "0.1.0",
            "ner_configured": ner_ok,
            "summarizer_configured": summ.configured if summ else False,
        }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
