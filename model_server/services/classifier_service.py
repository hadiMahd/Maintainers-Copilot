"""Classifier inference service with input-size checks and real artifact use."""

from __future__ import annotations

import logging

from model_server.domain.classifier import ClassifierPredictionResponse
from model_server.infra.classifier_loader import ClassifierLoader

logger = logging.getLogger(__name__)


class ClassifierService:
    """Orchestrates classifier inference using the loaded artifact."""

    def __init__(self, loader: ClassifierLoader):
        self._loader = loader

    def predict(
        self,
        text: str,
        request_id: str | None = None,
    ) -> ClassifierPredictionResponse:
        if not self._loader.is_loaded:
            raise RuntimeError("Classifier model is not loaded")
        if not text.strip():
            raise ValueError("Input text must not be empty for classification")

        label, confidence = self._loader.predict(text)
        return ClassifierPredictionResponse(
            label=label,
            confidence=confidence,
            model_version=self._loader.model_version,
            request_id=request_id,
        )
