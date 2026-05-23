"""Classifier artifact loader for model-server startup."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.domain.classifier import LABEL_ORDER
from app.infra.storage.classifier_artifacts import compute_artifact_sha256
from model_server.domain.classifier import (
    ClassifierErrorBody,
    ClassifierErrorDetails,
    ClassifierErrorResponse,
)

logger = logging.getLogger(__name__)

TRANSFORMER_WEIGHT_FILES = (
    "model.safetensors",
    "pytorch_model.bin",
)
TRANSFORMER_TOKENIZER_FILES = (
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.txt",
)


class ArtifactLoadError(Exception):
    """Raised when the classifier artifact cannot be loaded."""

    def __init__(self, reason: str, message: str):
        self.reason = reason
        self.message = message
        super().__init__(message)


class ClassifierLoader:
    """Loads and validates a classifier artifact from disk."""

    def __init__(self, artifact_dir: str | None = None, model_version: str | None = None):
        self._artifact_dir = Path(artifact_dir) if artifact_dir else None
        self._resolved_artifact_dir: Path | None = None
        self._model_version = model_version or "unknown"
        self._model: Any = None
        self._tokenizer: Any = None
        self._artifact_kind: str | None = None
        self._loaded = False
        self._failure_reason = "missing_artifact"
        self._failure_message = "Classifier model is not available"

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def artifact_kind(self) -> str | None:
        return self._artifact_kind

    def load(self) -> None:
        """Load the classifier artifact during lifespan startup."""
        try:
            artifact_dir = self._resolve_artifact_dir()
            if (artifact_dir / "model.joblib").exists():
                self._load_classical(artifact_dir)
            elif (artifact_dir / "model_card.json").exists():
                self._load_transformer(artifact_dir)
            else:
                raise ArtifactLoadError(
                    reason="invalid_artifact",
                    message=f"No supported classifier artifact found in {artifact_dir}",
                )

            self._loaded = True
            self._failure_reason = "missing_artifact"
            self._failure_message = "Classifier model is not available"
            logger.info(
                "Classifier artifact loaded from %s kind=%s version=%s",
                artifact_dir,
                self._artifact_kind,
                self._model_version,
            )
        except ArtifactLoadError as exc:
            self._loaded = False
            self._model = None
            self._tokenizer = None
            self._artifact_kind = None
            self._failure_reason = exc.reason
            self._failure_message = exc.message
            raise

    def unload(self) -> None:
        self._model = None
        self._tokenizer = None
        self._artifact_kind = None
        self._loaded = False
        logger.info("Classifier artifact unloaded")

    def predict(self, text: str) -> tuple[str, float | None]:
        """Run inference using the loaded artifact."""
        if not self._loaded or self._model is None:
            raise RuntimeError("Classifier model is not loaded")

        if self._artifact_kind == "classical":
            return self._predict_classical(text)
        if self._artifact_kind == "transformer":
            return self._predict_transformer(text)
        raise RuntimeError("Loaded classifier artifact has an unknown kind")

    def get_unavailable_error(self, request_id: str | None = None) -> ClassifierErrorResponse:
        return ClassifierErrorResponse(
            error=ClassifierErrorBody(
                code="classifier_model_unavailable",
                message=self._failure_message,
                request_id=request_id,
                details=ClassifierErrorDetails(reason=self._failure_reason),
            )
        )

    def _resolve_artifact_dir(self) -> Path:
        if self._artifact_dir is None:
            raise ArtifactLoadError(
                reason="missing_artifact",
                message="Classifier artifact directory not configured",
            )
        if not self._artifact_dir.exists():
            raise ArtifactLoadError(
                reason="missing_artifact",
                message=f"Classifier artifact directory not found: {self._artifact_dir}",
            )

        if self._contains_supported_artifact(self._artifact_dir):
            self._resolved_artifact_dir = self._artifact_dir
            return self._artifact_dir

        candidates = [
            child
            for child in sorted(self._artifact_dir.iterdir())
            if child.is_dir() and self._contains_supported_artifact(child)
        ]
        if len(candidates) == 1:
            self._resolved_artifact_dir = candidates[0]
            return candidates[0]
        if len(candidates) > 1:
            raise ArtifactLoadError(
                reason="invalid_artifact",
                message=f"Multiple classifier artifacts found under {self._artifact_dir}; configure a concrete path",
            )
        raise ArtifactLoadError(
            reason="invalid_artifact",
            message=f"No supported classifier artifact found under {self._artifact_dir}",
        )

    def _load_classical(self, artifact_dir: Path) -> None:
        try:
            import joblib
        except ImportError as exc:
            raise ArtifactLoadError(
                reason="startup_load_failed",
                message="joblib is required to load the classical classifier artifact",
            ) from exc

        model_path = artifact_dir / "model.joblib"
        if not model_path.exists():
            raise ArtifactLoadError(
                reason="invalid_artifact",
                message=f"Classical model file not found at {model_path}",
            )

        try:
            loaded = joblib.load(model_path)
        except Exception as exc:
            raise ArtifactLoadError(
                reason="startup_load_failed",
                message=f"Failed to load classical model artifact: {exc}",
            ) from exc

        # The dump notebook saves a dict {"vectorizer": ..., "model": clf, ...}.
        # Extract the actual sklearn estimator for inference.
        if isinstance(loaded, dict) and "model" in loaded:
            self._model = loaded["model"]
            self._model_metadata = {k: v for k, v in loaded.items() if k != "model"}
        else:
            self._model = loaded

        self._artifact_kind = "classical"
        config_path = artifact_dir / "config.json"
        if config_path.exists():
            with config_path.open() as handle:
                config = json.load(handle)
            self._model_version = config.get("version", self._model_version)

    def _load_transformer(self, artifact_dir: Path) -> None:
        model_card_path = artifact_dir / "model_card.json"
        if not model_card_path.exists():
            raise ArtifactLoadError(
                reason="invalid_artifact",
                message=f"Model card not found at {model_card_path}",
            )

        try:
            model_card = json.loads(model_card_path.read_text())
        except Exception as exc:
            raise ArtifactLoadError(
                reason="invalid_artifact",
                message=f"Failed to parse model card: {exc}",
            ) from exc

        expected_hash = model_card.get("artifact_sha256")
        if not expected_hash:
            raise ArtifactLoadError(
                reason="invalid_artifact",
                message="Transformer model card is missing artifact_sha256",
            )
        actual_hash = compute_artifact_sha256(artifact_dir)
        if actual_hash != expected_hash:
            raise ArtifactLoadError(
                reason="hash_mismatch",
                message=f"Artifact hash mismatch: expected {expected_hash}, got {actual_hash}",
            )

        if not any((artifact_dir / file_name).exists() for file_name in TRANSFORMER_WEIGHT_FILES):
            raise ArtifactLoadError(
                reason="invalid_artifact",
                message="Transformer artifact is missing model weights",
            )
        if not any(
            (artifact_dir / file_name).exists() for file_name in TRANSFORMER_TOKENIZER_FILES
        ):
            raise ArtifactLoadError(
                reason="invalid_artifact",
                message="Transformer artifact is missing tokenizer files",
            )

        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as exc:
            raise ArtifactLoadError(
                reason="startup_load_failed",
                message="transformers is required to load the transformer classifier artifact",
            ) from exc

        try:
            self._tokenizer = AutoTokenizer.from_pretrained(
                artifact_dir,
                local_files_only=True,
            )
            self._model = AutoModelForSequenceClassification.from_pretrained(
                artifact_dir,
                local_files_only=True,
            )
            self._model.eval()
        except Exception as exc:
            raise ArtifactLoadError(
                reason="startup_load_failed",
                message=f"Failed to load transformer classifier artifact: {exc}",
            ) from exc

        self._artifact_kind = "transformer"
        self._model_version = model_card.get("model_version", self._model_version)

    def _predict_classical(self, text: str) -> tuple[str, float | None]:
        # The dump notebook saves vectorizer and model separately.
        # If a vectorizer is present, transform text before predicting.
        vectorizer = None
        if hasattr(self, "_model_metadata") and "vectorizer" in self._model_metadata:
            vectorizer = self._model_metadata["vectorizer"]

        if vectorizer is not None:
            features = vectorizer.transform([text])
        else:
            features = [text]

        predicted = self._model.predict(features)[0]
        confidence = None
        if hasattr(self._model, "predict_proba"):
            probabilities = self._model.predict_proba(features)[0]
            confidence = float(max(probabilities))
        return str(predicted), confidence

    def _predict_transformer(self, text: str) -> tuple[str, float | None]:
        try:
            import torch
        except ImportError as exc:
            raise RuntimeError("torch is required for transformer inference") from exc

        encoded = self._tokenizer(
            text,
            truncation=True,
            padding=True,
            max_length=256,
            return_tensors="pt",
        )
        with torch.no_grad():
            outputs = self._model(**encoded)
            probabilities = torch.softmax(outputs.logits, dim=-1)[0]
            predicted_id = int(torch.argmax(probabilities).item())
            confidence = float(probabilities[predicted_id].item())

        label_lookup = getattr(self._model.config, "id2label", None) or dict(enumerate(LABEL_ORDER))
        predicted = label_lookup[predicted_id]
        return str(predicted).lower(), confidence

    @staticmethod
    def _contains_supported_artifact(path: Path) -> bool:
        return (path / "model.joblib").exists() or (path / "model_card.json").exists()
