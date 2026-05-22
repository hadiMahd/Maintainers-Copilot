"""Train the classical TF-IDF + Logistic Regression baseline classifier.

Reads the Phase 2 train and validation splits, trains a TF-IDF + LogReg
pipeline, saves predictions and metrics under artifacts/classifiers/classical/,
and optionally writes metrics.json for the shared evaluator.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

import yaml

from app.domain.classifier import PredictionRecord
from app.services.classifier_evaluation import (
    compute_metrics,
    save_predictions_jsonl,
)


def load_dataset(path: str) -> list[dict]:
    """Load a JSONL dataset split."""
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_label_mapping(path: str = "config/label_mapping.yml") -> dict:
    """Load the label mapping YAML."""
    with open(path) as f:
        return yaml.safe_load(f)


def train_classical_classifier(
    train_path: str = "data/processed/train.jsonl",
    val_path: str = "data/processed/validation.jsonl",
    test_path: str = "data/processed/test.jsonl",
    artifact_dir: str = "artifacts/classifiers/classical",
) -> None:
    """Train the classical baseline and save predictions, metrics, and model artifacts."""
    import joblib
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    # Load data
    train_data = load_dataset(train_path)
    test_data = load_dataset(test_path)

    # Prepare text and labels
    X_train = [r.get("classifier_text", "") for r in train_data]
    y_train = [r.get("mapped_label", r.get("label_mapped", "")) for r in train_data]
    X_test = [r.get("classifier_text", "") for r in test_data]
    y_test = [r.get("mapped_label", r.get("label_mapped", "")) for r in test_data]

    # Build pipeline
    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
            ("clf", LogisticRegression(max_iter=1000, random_state=42)),
        ]
    )

    # Train
    start_time = time.time()
    pipeline.fit(X_train, y_train)
    train_duration_ms = (time.time() - start_time) * 1000

    # Predict
    start_time = time.time()
    y_pred = pipeline.predict(X_test)
    infer_duration_ms = (time.time() - start_time) * 1000

    # Metrics
    metrics = compute_metrics(y_test, y_pred)
    metrics["train_duration_ms"] = train_duration_ms
    metrics["infer_duration_ms"] = infer_duration_ms

    # Build predictions
    predictions = []
    for i, (true_label, pred_label) in enumerate(zip(y_test, y_pred)):
        record_id = test_data[i].get("id", f"record-{i}")
        prob = pipeline.predict_proba([X_test[i]])[0]
        confidence = float(max(prob))
        predictions.append(
            PredictionRecord(
                record_id=record_id,
                approach="classical",
                label_true=true_label,
                label_predicted=pred_label,
                confidence=confidence,
                model_version="0.1.0",
                latency_ms=round(infer_duration_ms / len(X_test), 2),
            )
        )

    # Create artifact directory
    artifact_path = Path(artifact_dir)
    artifact_path.mkdir(parents=True, exist_ok=True)

    # Save predictions
    save_predictions_jsonl(predictions, str(artifact_path / "predictions.jsonl"))

    # Save metrics
    metrics_path = artifact_path / "metrics.json"
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".json", dir=str(artifact_path))
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(metrics, f, indent=2, default=str)
        os.replace(tmp_path, str(metrics_path))
    except Exception:
        os.unlink(tmp_path) if os.path.exists(tmp_path) else None
        raise

    # Save model
    model_path = artifact_path / "model.joblib"
    joblib.dump(pipeline, str(model_path))

    # Save model config
    config = {
        "model_type": "tfidf_logreg",
        "tfidf_max_features": 5000,
        "tfidf_ngram_range": [1, 2],
        "logreg_max_iter": 1000,
        "logreg_random_state": 42,
        "train_samples": len(train_data),
        "test_samples": len(test_data),
        "approach": "classical",
        "version": "0.1.0",
    }
    config_path = artifact_path / "config.json"
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".json", dir=str(artifact_path))
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(config, f, indent=2)
        os.replace(tmp_path, str(config_path))
    except Exception:
        os.unlink(tmp_path) if os.path.exists(tmp_path) else None
        raise

    print(
        f"Classical baseline trained. Metrics: accuracy={metrics['accuracy']:.4f}, macro_f1={metrics['macro_f1']:.4f}"
    )
    print(f"Artifacts saved to {artifact_dir}")


if __name__ == "__main__":
    train_classical_classifier()
