"""Compare all classifier approaches and produce one shared evaluation report.

Reads prediction files from classical, transformer, and LLM baseline approaches,
computes shared metrics, and writes evals/classifier_eval_report.json.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.domain.classifier import (
    ApproachMetrics,
    SkippedApproach,
)
from app.services.classifier_evaluation import (
    build_evaluation_report,
    compute_dataset_hash,
    compute_metrics,
    save_evaluation_report,
)


def load_approach_predictions(path: str) -> list[dict] | None:
    """Load predictions file, returning None if missing."""
    p = Path(path)
    if not p.exists():
        return None
    with open(p) as f:
        return [json.loads(line) for line in f if line.strip()]


def load_approach_metrics(path: str) -> dict | None:
    """Load metrics file, returning None if missing."""
    p = Path(path)
    if not p.exists():
        return None
    with open(p) as f:
        return json.load(f)


def load_approach_status(path: str) -> dict | None:
    """Load status.json for approaches that were skipped explicitly."""
    p = Path(path)
    if not p.exists():
        return None
    with open(p) as f:
        return json.load(f)


def calculate_approach_metrics(
    approach_name: str,
    predictions_path: str,
    metrics_path: str,
    test_hash: str,
) -> ApproachMetrics | SkippedApproach:
    """Calculate ApproachMetrics or SkippedApproach for one approach."""
    preds_data = load_approach_predictions(predictions_path)
    metrics_data = load_approach_metrics(metrics_path)
    status_data = load_approach_status(str(Path(predictions_path).parent / "status.json"))

    if status_data and status_data.get("status") == "skipped":
        return SkippedApproach(
            name=approach_name,
            skip_reason=status_data.get("skip_reason", f"{approach_name} was skipped"),
        )

    if preds_data is None and metrics_data is None:
        return SkippedApproach(
            name=approach_name,
            skip_reason=f"No predictions or metrics found for {approach_name}",
        )

    # Metrics-only fallback: if predictions are missing but metrics exist,
    # build ApproachMetrics from saved metrics (used for transformer when
    # predictions.jsonl was not generated during training).
    if preds_data is None:
        status = (metrics_data or {}).get("status")
        if status == "skipped":
            return SkippedApproach(
                name=approach_name,
                skip_reason=(metrics_data or {}).get(
                    "skip_reason",
                    f"{approach_name} did not produce predictions",
                ),
            )
        if metrics_data:
            return _build_metrics_only_approach(approach_name, metrics_data, predictions_path)
        return SkippedApproach(
            name=approach_name,
            skip_reason=f"{approach_name} metrics exist but predictions are missing",
        )

    # Load predictions if available (supports both PredictionRecord format
    # and dump-notebook format with true_label/predicted_label keys).
    y_true: list[str] = []
    y_pred: list[str] = []
    latency_values: list[float] = []
    if preds_data is not None:
        for r in preds_data:
            true_label = r.get("label_true") or r.get("true_label", "")
            pred_label = r.get("label_predicted") or r.get("predicted_label", "")
            y_true.append(true_label)
            y_pred.append(pred_label)
            if r.get("latency_ms") is not None:
                latency_values.append(r["latency_ms"])

    # Compute metrics or use saved ones
    computed_metrics = {}
    if y_true and y_pred:
        computed_metrics = compute_metrics(y_true, y_pred)

    # Merge with saved metrics (normalize HF metric names first)
    saved_metrics = _normalize_metrics(metrics_data or {})

    version = saved_metrics.get("version", saved_metrics.get("model_version"))
    if version is None and preds_data:
        version = preds_data[0].get("model_version") or preds_data[0].get("version")
    if version is None:
        version = "unknown"
    artifact_path_str = str(Path(predictions_path).parent)

    latency_summary = None
    if latency_values:
        latency_summary = {
            "p50": sorted(latency_values)[len(latency_values) // 2],
            "p95": sorted(latency_values)[int(len(latency_values) * 0.95)],
            "mean": sum(latency_values) / len(latency_values),
        }

    cost_summary = None
    if saved_metrics.get("secret_source") == "vault":
        cost_summary = saved_metrics.get("cost", None)

    return ApproachMetrics(
        name=approach_name,
        version=version,
        status="completed",
        accuracy=computed_metrics.get("accuracy", saved_metrics.get("accuracy")),
        macro_f1=computed_metrics.get("macro_f1", saved_metrics.get("macro_f1")),
        per_class_f1=computed_metrics.get("per_class_f1", saved_metrics.get("per_class_f1")),
        confusion_matrix=computed_metrics.get(
            "confusion_matrix", saved_metrics.get("confusion_matrix")
        ),
        latency=latency_summary,
        cost=cost_summary,
        artifact_path=artifact_path_str,
        predictions_path=predictions_path,
        metrics_path=metrics_path,
        config=saved_metrics.get("config"),
        provider_backend=saved_metrics.get("provider_backend"),
        tracing_backend=saved_metrics.get("tracing_backend"),
        secret_source=saved_metrics.get("secret_source"),
        run_id=saved_metrics.get("run_id"),
        run_logger_backend=saved_metrics.get("run_logger_backend"),
        minio_reference=saved_metrics.get("minio_reference"),
    )


def _normalize_metrics(saved_metrics: dict) -> dict:
    """Normalize transformer HF metric names to canonical project names.

    Maps eval_accuracy -> accuracy, eval_f1_macro -> macro_f1, etc.
    Preserves all other keys.
    """
    normalized: dict = dict(saved_metrics)
    key_map = {
        "eval_accuracy": "accuracy",
        "eval_f1_macro": "macro_f1",
        "test_accuracy": "accuracy",
        "test_macro_f1": "macro_f1",
    }
    for old_key, new_key in key_map.items():
        if old_key in normalized and new_key not in normalized:
            normalized[new_key] = normalized[old_key]
    return normalized


def _build_metrics_only_approach(
    approach_name: str,
    saved_metrics: dict,
    predictions_path: str,
) -> ApproachMetrics:
    """Build ApproachMetrics from saved metrics when predictions are missing."""
    metrics = _normalize_metrics(saved_metrics)
    version = metrics.get("version", metrics.get("model_version", "unknown"))
    artifact_path_str = str(Path(predictions_path).parent)

    latency_summary = None
    if metrics.get("eval_duration_ms"):
        latency_summary = {
            "mean": metrics["eval_duration_ms"],
        }

    return ApproachMetrics(
        name=approach_name,
        version=version,
        status="completed",
        accuracy=metrics.get("accuracy"),
        macro_f1=metrics.get("macro_f1"),
        per_class_f1=metrics.get("per_class_f1"),
        confusion_matrix=metrics.get("confusion_matrix"),
        latency=latency_summary,
        cost=metrics.get("cost"),
        artifact_path=artifact_path_str,
        predictions_path=None,
        metrics_path=str(Path(predictions_path).parent / "metrics.json"),
        config=metrics.get("config"),
        provider_backend=metrics.get("provider_backend"),
        secret_source=metrics.get("secret_source"),
        run_id=metrics.get("run_id"),
        run_logger_backend=metrics.get("run_logger_backend"),
        minio_reference=metrics.get("minio_reference"),
    )


def evaluate_classifiers(
    test_path: str = "data/processed/test.jsonl",
    classical_predictions: str = "artifacts/classifiers/classical/pandas_logreg/predictions.jsonl",
    classical_metrics: str = "artifacts/classifiers/classical/pandas_logreg/metrics.json",
    transformer_predictions: str = "artifacts/classifiers/transformer/predictions.jsonl",
    transformer_metrics: str = "artifacts/classifiers/transformer/metrics.json",
    llm_predictions: str = "artifacts/classifiers/llm_baseline/predictions.jsonl",
    llm_metrics: str = "artifacts/classifiers/llm_baseline/metrics.json",
    output_path: str = "evals/classifier_eval_report.json",
) -> None:
    """Evaluate all classifier approaches and write the shared report."""
    test_hash = compute_dataset_hash(test_path)

    approach_results: list[ApproachMetrics] = []
    skipped: list[SkippedApproach] = []

    for name, pred_path, metric_path in [
        ("classical", classical_predictions, classical_metrics),
        ("transformer", transformer_predictions, transformer_metrics),
        ("llm_baseline", llm_predictions, llm_metrics),
    ]:
        result = calculate_approach_metrics(name, pred_path, metric_path, test_hash)
        if isinstance(result, SkippedApproach):
            skipped.append(result)
        else:
            approach_results.append(result)

    report = build_evaluation_report(
        dataset_test_hash=test_hash,
        approach_results=approach_results,
        skipped_approaches=skipped,
        limitations=[
            "Classical baseline uses TF-IDF + LogReg with limited text features.",
            "Transformer results depend on local fine-tuning availability.",
            "LLM baseline may be skipped in environments without Azure OpenAI credentials.",
        ],
    )

    save_evaluation_report(report, output_path)

    print(f"Evaluation report saved to {output_path}")
    print(f"Completed approaches: {len(approach_results)}")
    print(f"Skipped approaches: {len(skipped)}")
    for s in skipped:
        print(f"  Skipped {s.name}: {s.skip_reason}")


if __name__ == "__main__":
    evaluate_classifiers()
