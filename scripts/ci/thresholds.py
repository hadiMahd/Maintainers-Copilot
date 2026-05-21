"""Threshold loading and validation helpers."""

from pathlib import Path
from typing import Any, Optional

import yaml


DEFAULT_THRESHOLD_PATH = Path("evals/eval_thresholds.yaml")


class ThresholdError(ValueError):
    pass


def load_thresholds(path: Optional[Path] = None) -> dict[str, Any]:
    p = path or DEFAULT_THRESHOLD_PATH
    if not p.exists():
        raise ThresholdError(f"Threshold file not found: {p}")
    with open(p) as f:
        data = yaml.safe_load(f) or {}
    return data


def validate_thresholds_nonzero(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    classifier = data.get("classifier") or {}
    rag = data.get("rag") or {}

    classifier_thresholds = [
        ("classifier.accuracy_min", classifier.get("accuracy_min")),
        ("classifier.macro_f1_min", classifier.get("macro_f1_min")),
    ]
    rag_thresholds = [
        ("rag.hit_at_5_min", rag.get("hit_at_5_min")),
        ("rag.mrr_at_10_min", rag.get("mrr_at_10_min")),
        ("rag.faithfulness_min", rag.get("faithfulness_min")),
        ("rag.answer_relevancy_min", rag.get("answer_relevancy_min")),
    ]

    for name, val in classifier_thresholds + rag_thresholds:
        if val is None:
            errors.append(f"{name}: missing")
        elif not isinstance(val, (int, float)):
            errors.append(f"{name}: not a number (got {type(val).__name__})")
        elif val <= 0:
            errors.append(f"{name}: must be greater than zero (got {val})")
        elif val != val:
            errors.append(f"{name}: is NaN")

    return errors


def check_threshold(value: float, threshold: float, name: str) -> tuple[bool, str]:
    if value >= threshold:
        return True, f"{name}: {value:.4f} >= threshold {threshold:.4f}"
    return False, f"{name}: {value:.4f} < threshold {threshold:.4f}"


def get_classifier_threshold(data: dict[str, Any], metric: str) -> float:
    classifier = data.get("classifier", {})
    key = f"{metric}_min"
    return float(classifier.get(key, 0.0))


def get_rag_threshold(data: dict[str, Any], metric: str) -> float:
    rag = data.get("rag", {})
    key = f"{metric}_min"
    return float(rag.get(key, 0.0))
