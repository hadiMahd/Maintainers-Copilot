"""Classifier evaluation service.

Provides shared metric calculation, evaluation report building, and
golden set validation used by all three classification approaches.
"""

from __future__ import annotations

import json
import hashlib
import tempfile
import os
import contextlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.domain.classifier import (
    APPROACH_NAMES,
    LABEL_ORDER,
    VALID_LABELS,
    ApproachMetrics,
    EvaluationReport,
    GoldenSetItem,
    PredictionRecord,
    SkippedApproach,
)


def compute_metrics(
    labels_true: list[str],
    labels_predicted: list[str],
    label_order: tuple[str, ...] | list[str] | None = None,
) -> dict[str, Any]:
    """Compute accuracy, macro-F1, per-class F1, and confusion matrix.

    Uses scikit-learn metrics with a stable label order.
    """
    from sklearn.metrics import (
        accuracy_score,
        confusion_matrix,
        f1_score,
    )

    order = label_order or LABEL_ORDER
    acc = accuracy_score(labels_true, labels_predicted)
    macro_f1 = f1_score(labels_true, labels_predicted, average="macro", labels=list(order), zero_division=0)
    per_class = f1_score(
        labels_true,
        labels_predicted,
        average=None,
        labels=list(order),
        zero_division=0,
    )
    per_class_f1 = {label: float(score) for label, score in zip(order, per_class)}
    cm = confusion_matrix(labels_true, labels_predicted, labels=list(order))

    return {
        "accuracy": float(acc),
        "macro_f1": float(macro_f1),
        "per_class_f1": per_class_f1,
        "confusion_matrix": cm.tolist(),
    }


def compute_dataset_hash(data_path: str) -> str:
    """Compute SHA-256 of a dataset file."""
    path = Path(data_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {data_path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_evaluation_report(
    dataset_test_hash: str,
    approach_results: list[ApproachMetrics],
    skipped_approaches: list[SkippedApproach] | None = None,
    limitations: list[str] | None = None,
) -> EvaluationReport:
    """Build an EvaluationReport from per-approach results."""
    return EvaluationReport(
        dataset_test_hash=dataset_test_hash,
        approaches=approach_results,
        skipped_approaches=skipped_approaches or [],
        generated_at=datetime.now(timezone.utc).isoformat(),
        limitations=limitations or [],
    )


def save_evaluation_report(report: EvaluationReport, path: str) -> None:
    """Atomically write evaluation report JSON to disk."""
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".json", dir=os.path.dirname(path) or ".")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            f.write(report.model_dump_json(indent=2))
        os.replace(tmp_path, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise


def validate_golden_set(items: list[GoldenSetItem]) -> list[str]:
    """Validate a golden set against the four project labels.

    Returns a list of error messages. An empty list means valid.
    """
    errors: list[str] = []
    if len(items) != 25:
        errors.append(f"Golden set must have exactly 25 items, got {len(items)}")

    label_counts: dict[str, int] = {}
    for item in items:
        if item.label not in VALID_LABELS:
            errors.append(f"Invalid label '{item.label}' in item {item.id}")
        label_counts[item.label] = label_counts.get(item.label, 0) + 1

    for label in VALID_LABELS:
        if label not in label_counts:
            errors.append(f"Golden set missing label '{label}'")

    return errors


def load_predictions_jsonl(path: str) -> list[PredictionRecord]:
    """Load predictions from a JSONL file."""
    records: list[PredictionRecord] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(PredictionRecord(**json.loads(line)))
    return records


def save_predictions_jsonl(predictions: list[PredictionRecord], path: str) -> None:
    """Atomically write predictions to a JSONL file."""
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".jsonl", dir=os.path.dirname(path) or ".")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            for pred in predictions:
                f.write(pred.model_dump_json() + "\n")
        os.replace(tmp_path, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise