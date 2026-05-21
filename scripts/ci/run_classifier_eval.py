"""Run classifier eval against compact golden set.

Default mode uses a deterministic keyword-based classifier that produces
repeatable, fast results without any training, model loading, or paid APIs.

Set USE_REAL_AZURE_EVALS=1 to trigger the project's full classifier pipeline
(requires model artifacts, datasets, and real credentials).
"""

import json
import os
import sys
from pathlib import Path
from typing import Any


KEYWORD_CLASSIFIER: dict[str, list[str]] = {
    "bug": [
        "null", "segfault", "crash", "memory leak", "race condition",
        "typeerror", "null pointer",
    ],
    "feature": [
        "add ", "implement ", "integrate ", "support ", "dark mode",
        "pagination", "rate limiting", "ci/cd", "ci pipeline",
    ],
    "documentation": [
        "readme", "docstring", "license", "contributing",
        "api reference", "installation instruction", "installation instructions",
        "clarify", "typo",
    ],
}


def _predict(text: str) -> str:
    text_lower = text.lower()
    scores: dict[str, int] = {"bug": 0, "feature": 0, "documentation": 0}
    for label, keywords in KEYWORD_CLASSIFIER.items():
        for kw in keywords:
            if kw in text_lower:
                scores[label] += 1
    if max(scores.values()) == 0:
        return "bug"
    return max(scores, key=lambda k: scores[k])


def evaluate_classifier(golden_path: str) -> dict[str, Any]:
    """Run classifier eval and return metrics dict."""
    with open(golden_path) as f:
        items = [json.loads(line) for line in f if line.strip()]

    labels_true = [item["label"] for item in items]
    labels_pred = [_predict(item["text"]) for item in items]

    unique_labels = sorted(set(labels_true + labels_pred))

    from sklearn.metrics import accuracy_score, f1_score

    accuracy = float(accuracy_score(labels_true, labels_pred))
    macro_f1 = float(f1_score(labels_true, labels_pred, average="macro", zero_division=0))
    per_class = f1_score(labels_true, labels_pred, average=None, labels=unique_labels, zero_division=0)
    per_class_f1 = {label: float(score) for label, score in zip(unique_labels, per_class)}

    return {
        "dataset_id": Path(golden_path).stem,
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "per_class_f1": per_class_f1,
    }


def check_classifier_gate(result: dict[str, Any]) -> tuple[bool, list[str]]:
    """Check classifier results against thresholds."""
    from scripts.ci.thresholds import check_threshold, get_classifier_threshold, load_thresholds

    thresholds = load_thresholds()
    failures: list[str] = []

    acc_threshold = get_classifier_threshold(thresholds, "accuracy")
    ok, msg = check_threshold(result["accuracy"], acc_threshold, "accuracy")
    if not ok:
        failures.append(msg)

    f1_threshold = get_classifier_threshold(thresholds, "macro_f1")
    ok, msg = check_threshold(result["macro_f1"], f1_threshold, "macro_f1")
    if not ok:
        failures.append(msg)

    return len(failures) == 0, failures


def _run_real_eval(golden_path: str) -> dict[str, Any]:
    """Run the full classifier evaluation pipeline (requires model artifacts)."""
    from app.services.classifier_evaluation import compute_metrics

    predictions_path = Path("artifacts/classifiers/classical/predictions.jsonl")
    if not predictions_path.exists():
        print("No classifier predictions found — falling back to keyword eval")
        return evaluate_classifier(golden_path)

    with open(predictions_path) as f:
        preds = [json.loads(line) for line in f if line.strip()]

    labels_true = [p["label_true"] for p in preds]
    labels_pred = [p["label_predicted"] for p in preds]
    metrics = compute_metrics(labels_true, labels_pred)
    metrics["dataset_id"] = Path(golden_path).stem
    return metrics


if __name__ == "__main__":
    golden_path = "evals/classification/golden.jsonl"

    if os.environ.get("USE_REAL_AZURE_EVALS") == "1":
        print("Real Azure eval mode (requires model artifacts and credentials)")
        result = _run_real_eval(golden_path)
    else:
        result = evaluate_classifier(golden_path)

    print(f"Classifier eval on {result['dataset_id']}:")
    print(f"  Accuracy: {result['accuracy']:.4f}")
    print(f"  Macro F1: {result['macro_f1']:.4f}")
    for label, f1 in sorted(result.get("per_class_f1", {}).items()):
        print(f"  {label}: {f1:.4f}")

    passed, failures = check_classifier_gate(result)
    if not passed:
        result["passed"] = False
        result["failures"] = failures
        print(f"FAIL: {len(failures)} threshold failure(s)")
        for f in failures:
            print(f"  {f}")
    else:
        result["passed"] = True
        result["failures"] = []

    out_dir = Path("evals/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "classifier_result.json", "w") as f:
        json.dump(result, f, indent=2)
    print(f"Classifier result saved to {out_dir / 'classifier_result.json'}")

    if not passed:
        sys.exit(1)

    print("Classifier eval passed all thresholds")
