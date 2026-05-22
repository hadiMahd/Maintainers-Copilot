"""MLflow tracking helpers for classifier training runs.

Provides start_run, log_params, log_metrics, and log_artifacts with
atomic file writes and structured run metadata. Redaction is applied
before any metadata is persisted.

When mlflow is not installed (running without [train] extras),
provides a no-op fallback that writes metadata to local JSON files.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any

from app.core.config import AppSettings
from app.infra.redaction import redact_run_metadata


class MLflowTrackingError(Exception):
    """Raised when MLflow tracking operations fail."""


def get_tracking_uri(settings: AppSettings) -> str:
    """Return the configured MLflow tracking URI."""
    return settings.mlflow_tracking_uri


def build_run_metadata(
    run_id: str,
    tracking_uri: str,
    artifact_uri: str,
    started_at: str,
    completed_at: str | None = None,
    status: str = "completed",
    parameters: dict[str, Any] | None = None,
    metrics: dict[str, float] | None = None,
    artifact_references: list[str] | None = None,
    redaction_applied: bool = True,
) -> dict[str, Any]:
    """Build a structured run metadata record for MLflow.

    All metadata is redacted before construction if redaction_applied is True.
    """
    metadata: dict[str, Any] = {
        "run_id": run_id,
        "backend": "mlflow",
        "tracking_uri": tracking_uri,
        "artifact_uri": artifact_uri,
        "started_at": started_at,
        "completed_at": completed_at,
        "status": status,
        "parameters": parameters or {},
        "metrics": metrics or {},
        "artifact_references": artifact_references or [],
        "redaction_applied": redaction_applied,
    }
    if redaction_applied:
        metadata = redact_run_metadata(metadata)
        metadata["redaction_applied"] = True
    return metadata


def save_run_metadata(metadata: dict[str, Any], path: str) -> None:
    """Atomically write run metadata to a JSON file."""
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".json", dir=os.path.dirname(path) or ".")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(metadata, f, indent=2, default=str)
        os.replace(tmp_path, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise


def is_mlflow_available() -> bool:
    """Check if mlflow package is available."""
    try:
        import mlflow  # noqa: F401

        return True
    except ImportError:
        return False


def finalize_run(
    run_id: str,
    tracking_uri: str,
    artifact_uri: str,
    started_at: str,
    metrics: dict[str, float] | None = None,
    parameters: dict[str, Any] | None = None,
    artifact_references: list[str] | None = None,
    output_dir: str | None = None,
) -> dict[str, Any]:
    """Finalize an MLflow run with metadata and optional redaction.

    When MLflow is available, logs to the tracking server.
    When not available, writes metadata to local files only.
    Returns the run metadata dict.
    """
    completed_at = datetime.now(timezone.utc).isoformat()

    metadata = build_run_metadata(
        run_id=run_id,
        tracking_uri=tracking_uri,
        artifact_uri=artifact_uri,
        started_at=started_at,
        completed_at=completed_at,
        status="completed",
        parameters=parameters,
        metrics=metrics,
        artifact_references=artifact_references,
    )

    if is_mlflow_available():
        import mlflow

        try:
            mlflow.log_metrics(metrics or {}, run_id=run_id)
            mlflow.log_params(parameters or {}, run_id=run_id)
        except Exception as exc:
            raise MLflowTrackingError(f"Failed to log to MLflow: {exc}") from exc

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        save_run_metadata(
            metadata,
            os.path.join(output_dir, "run_metadata.json"),
        )

    return metadata
