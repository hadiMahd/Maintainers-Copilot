"""Tests for classifier metric calculation and evaluation report building."""

import json
import tempfile
import os
from pathlib import Path

import pytest

from app.domain.classifier import (
    ApproachMetrics,
    EvaluationReport,
    GoldenSetItem,
    SkippedApproach,
)
from app.services.classifier_evaluation import (
    build_evaluation_report,
    compute_dataset_hash,
    compute_metrics,
    load_predictions_jsonl,
    save_evaluation_report,
    save_predictions_jsonl,
    validate_golden_set,
    LABEL_ORDER,
)


class TestComputeMetrics:
    """Tests for the shared metric computation function."""

    def test_perfect_accuracy(self):
        """All correct predictions produce accuracy 1.0."""
        labels_true = ["bug", "feature", "docs", "question"] * 5
        labels_pred = ["bug", "feature", "docs", "question"] * 5
        result = compute_metrics(labels_true, labels_pred)
        assert result["accuracy"] == 1.0

    def test_zero_accuracy(self):
        """All wrong predictions produce accuracy 0.0."""
        labels_true = ["bug"] * 4
        labels_pred = ["feature"] * 4
        result = compute_metrics(labels_true, labels_pred)
        assert result["accuracy"] == 0.0

    def test_per_class_f1_keys_match_label_order(self):
        """Per-class F1 keys match the stable label order."""
        labels_true = ["bug", "feature", "docs", "question"]
        labels_pred = ["bug", "feature", "docs", "question"]
        result = compute_metrics(labels_true, labels_pred)
        assert set(result["per_class_f1"].keys()) == set(LABEL_ORDER)

    def test_confusion_matrix_shape(self):
        """Confusion matrix has shape (num_labels, num_labels)."""
        labels_true = ["bug", "feature", "docs", "question"]
        labels_pred = ["bug", "feature", "docs", "question"]
        result = compute_metrics(labels_true, labels_pred)
        cm = result["confusion_matrix"]
        assert len(cm) == len(LABEL_ORDER)
        for row in cm:
            assert len(row) == len(LABEL_ORDER)

    def test_macro_f1_between_zero_and_one(self):
        """Macro-F1 is bounded between 0 and 1."""
        labels_true = ["bug", "feature", "docs", "question"]
        labels_pred = ["bug", "feature", "docs", "bug"]
        result = compute_metrics(labels_true, labels_pred)
        assert 0.0 <= result["macro_f1"] <= 1.0


class TestEvaluationReport:
    """Tests for evaluation report building and persistence."""

    def test_build_report_includes_skipped_approaches(self):
        """Skipped approaches are recorded, not silently omitted."""
        completed = ApproachMetrics(
            name="classical", version="0.1.0", status="completed", accuracy=0.8
        )
        skipped = SkippedApproach(name="llm_baseline", skip_reason="No Azure OpenAI credentials")
        report = build_evaluation_report(
            dataset_test_hash="abc123",
            approach_results=[completed],
            skipped_approaches=[skipped],
        )
        assert len(report.skipped_approaches) == 1
        assert report.skipped_approaches[0].name == "llm_baseline"

    def test_report_stable_label_order(self):
        """Report uses the stable label order."""
        report = build_evaluation_report(
            dataset_test_hash="abc123",
            approach_results=[],
        )
        assert report.label_order == list(LABEL_ORDER)

    def test_save_and_load_report_roundtrip(self, tmp_path):
        """Report survives save/load roundtrip."""
        completed = ApproachMetrics(
            name="classical", version="0.1.0", status="completed", accuracy=0.85
        )
        report = build_evaluation_report(
            dataset_test_hash="abc123",
            approach_results=[completed],
        )
        path = str(tmp_path / "eval_report.json")
        save_evaluation_report(report, path)
        loaded = json.loads(Path(path).read_text())
        assert loaded["dataset_test_hash"] == "abc123"
        assert loaded["approaches"][0]["name"] == "classical"


class TestGoldenSetValidation:
    """Tests for golden set validation."""

    def test_valid_golden_set(self):
        """A golden set with 25 items and all labels passes validation."""
        items = []
        labels = list(LABEL_ORDER)
        for i in range(25):
            items.append(GoldenSetItem(
                id=f"golden-{i:03d}",
                title=f"Title {i}",
                body=f"Body {i}",
                label=labels[i % len(labels)],
            ))
        errors = validate_golden_set(items)
        assert errors == []

    def test_wrong_count_fails(self):
        """A golden set with wrong count fails validation."""
        items = [
            GoldenSetItem(id="g1", title="t", body="b", label="bug"),
        ]
        errors = validate_golden_set(items)
        assert any("25" in e for e in errors)

    def test_missing_label_fails(self):
        """A golden set missing a label fails validation."""
        items = [GoldenSetItem(id=f"g{i}", title=f"t{i}", body=f"b{i}", label="bug") for i in range(25)]
        errors = validate_golden_set(items)
        assert any("missing label" in e for e in errors)

    def test_invalid_label_fails(self):
        """A golden set with an invalid label fails validation."""
        items = [
            GoldenSetItem(id=f"g{i}", title=f"t{i}", body=f"b{i}", label="invalid_label")
            for i in range(25)
        ]
        errors = validate_golden_set(items)
        assert any("Invalid label" in e for e in errors)


class TestDatasetHash:
    """Tests for dataset hash computation."""

    def test_dataset_hash_deterministic(self, tmp_path):
        """Same content produces same hash."""
        path = tmp_path / "data.jsonl"
        path.write_text('{"id": 1}\n{"id": 2}\n')
        hash1 = compute_dataset_hash(str(path))
        hash2 = compute_dataset_hash(str(path))
        assert hash1 == hash2

    def test_dataset_hash_missing_file_raises(self):
        """Missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            compute_dataset_hash("/nonexistent/path/data.jsonl")


class TestPredictionsJsonl:
    """Tests for prediction JSONL save/load."""

    def test_save_and_load_predictions(self, tmp_path):
        """Predictions survive save/load roundtrip."""
        from app.domain.classifier import PredictionRecord

        preds = [
            PredictionRecord(
                record_id="r1", approach="classical", label_true="bug",
                label_predicted="bug", model_version="0.1.0", confidence=0.9,
            ),
            PredictionRecord(
                record_id="r2", approach="classical", label_true="feature",
                label_predicted="docs", model_version="0.1.0", confidence=0.6,
            ),
        ]
        path = str(tmp_path / "preds.jsonl")
        save_predictions_jsonl(preds, path)
        loaded = load_predictions_jsonl(path)
        assert len(loaded) == 2
        assert loaded[0].record_id == "r1"
        assert loaded[1].label_predicted == "docs"