"""Model server domain package."""

from model_server.domain.classifier import (
    ClassifierErrorBody,
    ClassifierErrorDetails,
    ClassifierErrorResponse,
    ClassifierPredictionResponse,
)

__all__ = [
    "ClassifierErrorBody",
    "ClassifierErrorDetails",
    "ClassifierErrorResponse",
    "ClassifierPredictionResponse",
]
