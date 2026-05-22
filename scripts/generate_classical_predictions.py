"""Generate classical baseline predictions from the saved pandas artifact."""

import json
import time

import joblib

from app.domain.classifier import PredictionRecord
from app.services.classifier_evaluation import save_predictions_jsonl


def generate_classical_predictions(
    test_path: str = "data/processed/test.jsonl",
    model_path: str = "artifacts/classifiers/classical/pandas_logreg/model.joblib",
    output_path: str = "artifacts/classifiers/classical/pandas_logreg/predictions.jsonl",
) -> None:
    """Load the saved classical model and generate predictions on the test split."""
    artifact = joblib.load(model_path)
    vectorizer = artifact["vectorizer"]
    model = artifact["model"]
    artifact["labels"]  # ['bug', 'feature', 'docs', 'question']

    # Load test records
    test_records = []
    with open(test_path) as f:
        for line in f:
            line = line.strip()
            if line:
                test_records.append(json.loads(line))

    # Extract texts
    texts = [r["classifier_text"] for r in test_records]

    # Run inference
    start_time = time.monotonic()
    X_test = vectorizer.transform(texts)
    y_pred = model.predict(X_test)
    probabilities = model.predict_proba(X_test)
    elapsed_ms = (time.monotonic() - start_time) * 1000

    per_request_latency = round(elapsed_ms / max(len(test_records), 1), 2)

    # Build predictions
    predictions: list[PredictionRecord] = []
    for i, record in enumerate(test_records):
        pred_label = y_pred[i]
        confidence = float(max(probabilities[i]))
        predictions.append(
            PredictionRecord(
                record_id=record["id"],
                approach="classical",
                label_true=record["mapped_label"],
                label_predicted=pred_label,
                confidence=round(confidence, 6),
                model_version="0.1.0",
                latency_ms=per_request_latency,
            )
        )

    save_predictions_jsonl(predictions, output_path)
    print(f"Wrote {len(predictions)} classical predictions to {output_path}")


if __name__ == "__main__":
    generate_classical_predictions()
