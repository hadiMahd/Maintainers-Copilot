"""Classifier prediction endpoint route."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.domain.classifier import ClassifierRequest
from model_server.domain.classifier import (
    ClassifierErrorBody,
    ClassifierErrorDetails,
    ClassifierErrorResponse,
    ClassifierPredictionResponse,
)
from model_server.services.classifier_service import ClassifierService

router = APIRouter(prefix="/classifier", tags=["classifier"])


@router.post(
    "/predict",
    response_model=ClassifierPredictionResponse,
    responses={
        422: {"model": ClassifierErrorResponse},
        500: {"model": ClassifierErrorResponse},
        503: {"model": ClassifierErrorResponse},
    },
)
async def predict(
    request_body: ClassifierRequest, request: Request
) -> ClassifierPredictionResponse | ClassifierErrorResponse:
    """Predict the issue label for the given title, body, or comments.

    Returns a typed label, optional confidence, and semantic model_version.
    Returns 503 with a structured error if the model is not available.
    """
    from model_server.infra.classifier_loader import ClassifierLoader

    loader: ClassifierLoader | None = getattr(request.app.state, "classifier_loader", None)
    if loader is None or not loader.is_loaded:
        error_response = (
            ClassifierErrorResponse(
                error=ClassifierErrorBody(
                    code="classifier_model_unavailable",
                    message="Classifier model is not available",
                    request_id=getattr(request.state, "request_id", None),
                    details=ClassifierErrorDetails(reason="missing_artifact"),
                )
            )
            if loader is None
            else loader.get_unavailable_error(getattr(request.state, "request_id", None))
        )
        return JSONResponse(
            status_code=503,
            content=error_response.model_dump(exclude_none=True),
        )

    service = ClassifierService(loader)
    text = request_body.classifier_text()

    if not text.strip():
        error_body = ClassifierErrorBody(
            code="invalid_classifier_input",
            message="At least one text field must be non-empty",
            request_id=getattr(request.state, "request_id", None),
        )
        return JSONResponse(
            status_code=422,
            content={"error": error_body.model_dump(exclude_none=True)},
        )

    try:
        return service.predict(
            text=text,
            request_id=getattr(request.state, "request_id", None),
        )
    except ValueError as exc:
        error_body = ClassifierErrorBody(
            code="invalid_classifier_input",
            message=str(exc),
            request_id=getattr(request.state, "request_id", None),
        )
        return JSONResponse(
            status_code=422,
            content={"error": error_body.model_dump(exclude_none=True)},
        )
    except Exception:
        error_body = ClassifierErrorBody(
            code="internal_error",
            message="An unexpected error occurred during classification",
            request_id=getattr(request.state, "request_id", None),
        )
        return JSONResponse(
            status_code=500,
            content={"error": error_body.model_dump(exclude_none=True)},
        )
