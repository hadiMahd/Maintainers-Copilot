"""Classifier domain models for issue classification."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

VALID_LABELS = ("bug", "feature", "docs", "question")
LABEL_ORDER = list(VALID_LABELS)
APPROACH_NAMES = ("classical", "transformer", "llm_baseline")
SEMVER_PATTERN = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:[-+][A-Za-z0-9.-]+)?$"
)

# NOTE: This is NOT the canonical project label order.
# The canonical order for all project reports, confusion matrices, and
# evaluation is: bug, feature, docs, question (see LABEL_ORDER above).
#
# This alphabetical ordering exists solely because sklearn's LabelEncoder
# sorts alphabetically, and the DistilBERT training notebook uses
# LabelEncoder. The transformer model must use this exact ordering
# to stay compatible with the dump artifact.
TRANSFORMER_ALPHABETICAL_LABEL_IDS = {
    "bug": 0,
    "docs": 1,
    "feature": 2,
    "question": 3,
}


class PredictionRecord(BaseModel):
    """One prediction for one dataset record."""

    record_id: str
    approach: str
    label_true: str
    label_predicted: str
    confidence: float | None = None
    model_version: str
    latency_ms: float | None = None
    cost_usd: float | None = None


class ApproachMetrics(BaseModel):
    """Per-approach metrics block inside the evaluation report."""

    name: str
    version: str
    status: Literal["completed", "skipped", "failed"]
    accuracy: float | None = None
    macro_f1: float | None = None
    per_class_f1: dict[str, float] | None = None
    confusion_matrix: list[list[int]] | None = None
    latency: dict[str, float] | None = None
    cost: dict[str, float] | None = None
    skip_reason: str | None = None
    predictions_path: str | None = None
    metrics_path: str | None = None
    artifact_path: str | None = None
    config: dict | None = None
    provider_backend: str | None = None
    tracing_backend: str | None = None
    secret_source: str | None = None
    run_id: str | None = None
    run_logger_backend: str | None = None
    minio_reference: str | None = None


class SkippedApproach(BaseModel):
    """Record of a skipped approach in the evaluation report."""

    name: str
    skip_reason: str


class EvaluationReport(BaseModel):
    """One comparable report spanning all approaches."""

    dataset_test_hash: str
    label_order: list[str] = Field(default_factory=lambda: list(LABEL_ORDER))
    approaches: list[ApproachMetrics]
    skipped_approaches: list[SkippedApproach] = Field(default_factory=list)
    generated_at: str
    limitations: list[str] = Field(default_factory=list)


class GoldenSetItem(BaseModel):
    """One item in the 25-example golden set."""

    id: str
    title: str
    body: str
    comments: str | None = None
    label: str
    source_url: str | None = None


class ModelCard(BaseModel):
    """Metadata record for a deployable transformer artifact."""

    model_version: str
    approach: Literal["transformer"] = "transformer"
    architecture_name: str
    training_data_hash: str
    artifact_sha256: str
    hyperparameters: dict
    freeze_policy: str
    metrics: dict
    training_run_id: str | None = None
    run_logger_backend: str = "mlflow"
    training_plot_paths: list[str] = Field(default_factory=list)
    minio_reference: str | None = None
    intended_use: str = "issue_classification"
    limitations: list[str] = Field(default_factory=list)
    redaction_applied: bool = True

    @field_validator("model_version")
    @classmethod
    def validate_model_version(cls, value: str) -> str:
        if not SEMVER_PATTERN.match(value):
            raise ValueError("model_version must be a semantic version string")
        return value


class ArtifactManifest(BaseModel):
    """Portable record stored in MinIO for the selected classifier."""

    model_version: str
    approach: str
    artifact_sha256: str
    training_data_hash: str
    source_artifact_path: str
    minio_object_key: str
    uploaded_at: str


class ClassifierRequest(BaseModel):
    """Input payload for the model-server classifier endpoint."""

    title: str | None = Field(default=None, min_length=1, max_length=512)
    body: str | None = Field(default=None, min_length=1, max_length=16000)
    comments: list[str] | None = Field(default=None, max_length=100)

    @field_validator("comments")
    @classmethod
    def validate_comment_lengths(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            for i, comment in enumerate(v):
                if not comment.strip():
                    raise ValueError(f"Comment at index {i} must not be empty")
                if len(comment) > 4000:
                    raise ValueError(f"Comment at index {i} exceeds 4000 characters: {len(comment)} chars")
        return v

    @model_validator(mode="after")
    def validate_at_least_one_text_field(self) -> ClassifierRequest:
        has_title = bool(self.title and self.title.strip())
        has_body = bool(self.body and self.body.strip())
        has_comments = bool(self.comments)
        if not any((has_title, has_body, has_comments)):
            raise ValueError("At least one of title, body, or comments must be provided")
        return self

    def classifier_text(self) -> str:
        """Build the combined text for classification."""
        parts: list[str] = []
        if self.title:
            parts.append(self.title)
        if self.body:
            parts.append(self.body)
        if self.comments:
            parts.extend(self.comments)
        return "\n\n".join(parts)


class ClassifierPrediction(BaseModel):
    """Typed classifier inference result."""

    label: Literal["bug", "feature", "docs", "question"]
    confidence: float | None = None
    model_version: str
    request_id: str | None = None

    @field_validator("model_version")
    @classmethod
    def validate_model_version(cls, value: str) -> str:
        if not SEMVER_PATTERN.match(value):
            raise ValueError("model_version must be a semantic version string")
        return value


class ClassifierUnavailableError(BaseModel):
    """Structured error when inference cannot use a valid model."""

    code: Literal["classifier_model_unavailable"]
    message: str
    request_id: str | None = None
    reason: Literal["missing_artifact", "invalid_artifact", "hash_mismatch", "startup_load_failed"]
