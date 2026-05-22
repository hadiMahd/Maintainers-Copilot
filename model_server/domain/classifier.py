"""Model server classifier domain models.

Reuses the shared classifier schemas from app.domain.classifier for
request, response, and error types, and adds model-server-specific
prediction and model-loading models.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ClassifierPredictionResponse(BaseModel):
    """HTTP response for a successful classifier prediction."""

    label: Literal["bug", "feature", "docs", "question"]
    confidence: float | None = None
    model_version: str
    request_id: str | None = None


class ClassifierErrorResponse(BaseModel):
    """HTTP response for classifier errors."""

    error: ClassifierErrorBody


class ClassifierErrorBody(BaseModel):
    """Error body for classifier error responses."""

    code: Literal["invalid_classifier_input", "classifier_model_unavailable", "internal_error"]
    message: str
    request_id: str | None = None
    details: ClassifierErrorDetails | None = None


class ClassifierErrorDetails(BaseModel):
    """Error details for classifier errors."""

    reason: Literal["missing_artifact", "invalid_artifact", "hash_mismatch", "startup_load_failed"]
