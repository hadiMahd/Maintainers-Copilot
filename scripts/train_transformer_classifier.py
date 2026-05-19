"""Train the DistilBERT transformer classifier."""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from app.domain.classifier import (
    LABEL_ORDER,
    TRANSFORMER_ALPHABETICAL_LABEL_IDS,
    ModelCard,
    PredictionRecord,
)
from app.infra.mlflow.tracking import build_run_metadata, save_run_metadata
from app.infra.redaction import redact_model_card
from app.infra.storage.classifier_artifacts import (
    compute_artifact_sha256,
    compute_training_data_hash,
    write_artifact_sha256,
)
from app.services.classifier_evaluation import compute_metrics, save_predictions_jsonl


def train_transformer_classifier(
    train_path: str = "data/processed/train.jsonl",
    val_path: str = "data/processed/validation.jsonl",
    test_path: str = "data/processed/test.jsonl",
    artifact_dir: str = "artifacts/classifiers/transformer",
    mlflow_tracking_uri: str | None = None,
    mlflow_experiment_name: str = "issue-classifier-transformer",
) -> None:
    """Train DistilBERT when optional training dependencies are available."""
    modules = _import_training_dependencies()
    if modules is None:
        _write_skipped_artifact(
            artifact_dir,
            "torch/transformers/datasets not installed (install with: uv sync --extra train)",
        )
        print("Transformer training skipped: training dependencies are not installed.")
        return

    (
        dataset_class,
        auto_model_for_sequence_classification,
        auto_tokenizer,
        trainer_class,
        training_arguments_class,
    ) = modules

    train_records = _load_dataset(train_path)
    validation_records = _load_dataset(val_path)
    test_records = _load_dataset(test_path)

    train_examples = _normalize_examples(train_records)
    validation_examples = _normalize_examples(validation_records)
    test_examples = _normalize_examples(test_records)

    artifact_path = Path(artifact_dir)
    artifact_path.mkdir(parents=True, exist_ok=True)
    plots_dir = artifact_path / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    tokenizer = auto_tokenizer.from_pretrained("distilbert-base-uncased")
    train_dataset = _build_dataset(dataset_class, train_examples, tokenizer)
    validation_dataset = _build_dataset(dataset_class, validation_examples, tokenizer)
    test_dataset = _build_dataset(dataset_class, test_examples, tokenizer)

    # Use the alphabetical label ordering that matches the dump notebook.
    label_to_id = TRANSFORMER_ALPHABETICAL_LABEL_IDS
    id_to_label = {index: label for label, index in label_to_id.items()}

    model = auto_model_for_sequence_classification.from_pretrained(
        "distilbert-base-uncased",
        num_labels=len(label_to_id),
        id2label=id_to_label,
        label2id=label_to_id,
    )

    # Match dump TrainingArguments exactly.
    training_args = training_arguments_class(
        output_dir=str(artifact_path / "trainer_output"),
        num_train_epochs=3,
        learning_rate=2e-5,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        weight_decay=0.01,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        logging_steps=10,
        report_to="none",
        disable_tqdm=False,
    )

    # Match dump: add compute_metrics to Trainer, use processing_class.
    trainer = trainer_class(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=validation_dataset,
        processing_class=tokenizer,
        compute_metrics=_compute_metrics,
    )

    run_id = f"transformer-{uuid.uuid4().hex[:12]}"
    started_at = datetime.now(UTC).isoformat()
    tracking_uri = mlflow_tracking_uri or os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
    artifact_uri = str(artifact_path.resolve())

    train_started = time.monotonic()
    run = None
    mlflow = None
    try:
        try:
            import mlflow as _mlflow

            mlflow = _mlflow
            mlflow.set_tracking_uri(tracking_uri)
            mlflow.set_experiment(mlflow_experiment_name)
            run = mlflow.start_run(run_name=run_id)
            run_id = run.info.run_id
            artifact_uri = run.info.artifact_uri
        except Exception:
            mlflow = None
            run = None

        trainer.train()
        train_duration_ms = (time.monotonic() - train_started) * 1000

        # Match dump: use trainer.evaluate() on the test set.
        eval_started = time.monotonic()
        eval_results = trainer.evaluate(test_dataset)
        eval_duration_ms = (time.monotonic() - eval_started) * 1000

        # Build predictions from eval_results and raw logits for confidence.
        prediction_output = trainer.predict(test_dataset)
        logits = np.asarray(prediction_output.predictions)
        probabilities = _softmax(logits)
        predicted_ids = probabilities.argmax(axis=1)
        predicted_labels = [id_to_label[int(index)] for index in predicted_ids]
        true_labels = [example["label"] for example in test_examples]

        # Metrics: shared evaluator + Hugging Face eval metrics.
        shared_metrics = compute_metrics(true_labels, predicted_labels)
        metrics: dict[str, Any] = {
            "accuracy": shared_metrics["accuracy"],
            "macro_f1": shared_metrics["macro_f1"],
            "per_class_f1": shared_metrics.get("per_class_f1"),
            "confusion_matrix": shared_metrics.get("confusion_matrix"),
            "train_duration_ms": round(train_duration_ms, 2),
            "eval_duration_ms": round(eval_duration_ms, 2),
            "provider_backend": "transformers",
            "run_id": run_id,
            "run_logger_backend": "mlflow",
        }
        # Merge HF eval metrics (eval_accuracy, eval_f1_macro, etc.)
        for key, value in eval_results.items():
            if key not in metrics:
                metrics[key] = value

        predictions: list[PredictionRecord] = []
        per_request_latency = round(eval_duration_ms / max(len(test_examples), 1), 2)
        for example, predicted_label, confidence in zip(
            test_examples,
            predicted_labels,
            probabilities.max(axis=1),
            strict=False,
        ):
            predictions.append(
                PredictionRecord(
                    record_id=example["record_id"],
                    approach="transformer",
                    label_true=example["label"],
                    label_predicted=predicted_label,
                    confidence=round(float(confidence), 6),
                    model_version="0.1.0",
                    latency_ms=per_request_latency,
                )
            )

        save_predictions_jsonl(predictions, str(artifact_path / "predictions.jsonl"))
        _atomic_write_json(metrics, str(artifact_path / "metrics.json"))

        # Match dump: trainer.save_model() persists model + tokenizer.
        trainer.save_model(artifact_path)

        plot_paths = _write_training_plot_artifacts(
            plots_dir=plots_dir,
            log_history=trainer.state.log_history,
            metrics=metrics,
        )

        training_data_hash = compute_training_data_hash(train_path)
        artifact_sha256 = compute_artifact_sha256(artifact_path)
        write_artifact_sha256(artifact_path, artifact_sha256)

        model_card = ModelCard(
            model_version="0.1.0",
            architecture_name="distilbert-base-uncased",
            training_data_hash=training_data_hash,
            artifact_sha256=artifact_sha256,
            hyperparameters={
                "learning_rate": training_args.learning_rate,
                "num_train_epochs": training_args.num_train_epochs,
                "per_device_train_batch_size": training_args.per_device_train_batch_size,
                "per_device_eval_batch_size": training_args.per_device_eval_batch_size,
                "weight_decay": training_args.weight_decay,
            },
            freeze_policy="none",
            metrics=metrics,
            training_run_id=run_id,
            training_plot_paths=plot_paths,
        )
        _atomic_write_json(
            redact_model_card(model_card.model_dump()),
            str(artifact_path / "model_card.json"),
        )

        run_metadata = build_run_metadata(
            run_id=run_id,
            tracking_uri=tracking_uri,
            artifact_uri=artifact_uri,
            started_at=started_at,
            completed_at=datetime.now(UTC).isoformat(),
            status="completed",
            parameters=model_card.hyperparameters,
            metrics={
                "accuracy": float(metrics["accuracy"]),
                "macro_f1": float(metrics["macro_f1"]),
            },
            artifact_references=plot_paths + ["metrics.json", "predictions.jsonl", "artifact.sha256"],
        )
        save_run_metadata(run_metadata, str(artifact_path / "run_metadata.json"))

        if mlflow is not None and run is not None:
            with contextlib.suppress(Exception):
                mlflow.log_params(model_card.hyperparameters)
                mlflow.log_metrics(
                    {
                        "accuracy": float(metrics["accuracy"]),
                        "macro_f1": float(metrics["macro_f1"]),
                    }
                )
                mlflow.log_artifacts(str(plots_dir), artifact_path="plots")
                mlflow.log_artifact(str(artifact_path / "metrics.json"))
                mlflow.log_artifact(str(artifact_path / "predictions.jsonl"))
                mlflow.log_artifact(str(artifact_path / "artifact.sha256"))

        print(
            "Transformer baseline trained. "
            f"Metrics: accuracy={metrics['accuracy']:.4f}, macro_f1={metrics['macro_f1']:.4f}"
        )
        print(f"Artifacts saved to {artifact_dir}")
    finally:
        if mlflow is not None and run is not None:
            with contextlib.suppress(Exception):
                mlflow.end_run()
        shutil_path = artifact_path / "trainer_output"
        if shutil_path.exists():
            import shutil

            shutil.rmtree(shutil_path, ignore_errors=True)


def _import_training_dependencies() -> tuple[Any, Any, Any, Any, Any] | None:
    try:
        from datasets import Dataset
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            Trainer,
            TrainingArguments,
        )
    except ImportError:
        return None
    return (
        Dataset,
        AutoModelForSequenceClassification,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
    )


def _load_dataset(path: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    if not records:
        raise ValueError(f"Dataset file is empty: {path}")
    return records


def _normalize_examples(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        text = record.get("classifier_text") or record.get("text_for_classifier") or ""
        label = record.get("mapped_label", record.get("label_mapped", ""))
        if not text.strip():
            raise ValueError(f"Dataset record at index {index} is missing classifier text")
        if label not in TRANSFORMER_ALPHABETICAL_LABEL_IDS:
            raise ValueError(f"Dataset record at index {index} has unsupported label: {label}")
        examples.append(
            {
                "record_id": record.get("id", f"record-{index}"),
                "text": text,
                "label": label,
            }
        )
    return examples


def _build_dataset(dataset_cls: Any, examples: list[dict[str, Any]], tokenizer: Any) -> Any:
    # Use the alphabetical label ordering that matches the dump notebook
    # (sklearn LabelEncoder sorts alphabetically).
    label_to_id = TRANSFORMER_ALPHABETICAL_LABEL_IDS
    dataset = dataset_cls.from_list(
        [
            {"text": example["text"], "labels": label_to_id[example["label"]]}
            for example in examples
        ]
    )
    # Match dump tokenization: padding=True (not "max_length"),
    # truncation=True, max_length=512.
    return dataset.map(
        lambda batch: tokenizer(
            batch["text"],
            padding=True,
            truncation=True,
            max_length=512,
        ),
        batched=True,
    )


def _compute_metrics(eval_pred: Any) -> dict[str, float]:
    """Compute accuracy and macro-F1 for the Hugging Face Trainer.

    Matches the dump notebook compute_metrics function exactly.
    """
    from sklearn.metrics import accuracy_score, f1_score

    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, predictions),
        "f1_macro": f1_score(labels, predictions, average="macro"),
    }


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits, axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=1, keepdims=True)


def _write_training_plot_artifacts(
    *,
    plots_dir: Path,
    log_history: list[dict[str, Any]],
    metrics: dict[str, Any],
) -> list[str]:
    history_path = plots_dir / "training_log_history.json"
    summary_path = plots_dir / "evaluation_summary.json"
    _atomic_write_json(log_history, str(history_path))
    _atomic_write_json(metrics, str(summary_path))
    return [
        str(history_path.relative_to(plots_dir.parent)),
        str(summary_path.relative_to(plots_dir.parent)),
    ]


def _write_skipped_artifact(artifact_dir: str, reason: str) -> None:
    artifact_path = Path(artifact_dir)
    artifact_path.mkdir(parents=True, exist_ok=True)
    status = {
        "status": "skipped",
        "approach": "transformer",
        "version": "0.1.0",
        "skip_reason": reason,
    }
    _atomic_write_json(status, str(artifact_path / "status.json"))


def _atomic_write_json(data: Any, path: str) -> None:
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".json", dir=os.path.dirname(path) or ".")
    try:
        with os.fdopen(tmp_fd, "w") as handle:
            json.dump(data, handle, indent=2, default=str)
        os.replace(tmp_path, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise


if __name__ == "__main__":
    train_transformer_classifier()
