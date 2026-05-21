"""Unit tests for threshold helper validation."""

import pytest
import tempfile
from pathlib import Path

from scripts.ci.thresholds import (
    ThresholdError,
    check_threshold,
    get_classifier_threshold,
    get_rag_threshold,
    load_thresholds,
    validate_thresholds_nonzero,
)


class TestThresholdValidation:
    def test_nonzero_thresholds_pass(self):
        data = {
            "classifier": {"accuracy_min": 0.55, "macro_f1_min": 0.50},
            "rag": {
                "hit_at_5_min": 0.10,
                "mrr_at_10_min": 0.10,
                "faithfulness_min": 0.10,
                "answer_relevancy_min": 0.10,
            },
        }
        errors = validate_thresholds_nonzero(data)
        assert errors == []

    def test_zero_threshold_fails(self):
        data = {"classifier": {"accuracy_min": 0.0, "macro_f1_min": 0.50}, "rag": {}}
        errors = validate_thresholds_nonzero(data)
        assert len(errors) >= 1
        assert "accuracy_min" in errors[0]

    def test_missing_threshold_fails(self):
        data = {"classifier": {}, "rag": {}}
        errors = validate_thresholds_nonzero(data)
        assert len(errors) >= 1
        assert any("missing" in e for e in errors)

    def test_negative_threshold_fails(self):
        data = {
            "classifier": {"accuracy_min": -0.1, "macro_f1_min": 0.50},
            "rag": {
                "hit_at_5_min": 0.10,
                "mrr_at_10_min": 0.10,
                "faithfulness_min": 0.10,
                "answer_relevancy_min": 0.10,
            },
        }
        errors = validate_thresholds_nonzero(data)
        assert len(errors) >= 1
        assert "accuracy_min" in errors[0]

    def test_nan_threshold_fails(self):
        data = {
            "classifier": {"accuracy_min": float("nan"), "macro_f1_min": 0.50},
            "rag": {
                "hit_at_5_min": 0.10,
                "mrr_at_10_min": 0.10,
                "faithfulness_min": 0.10,
                "answer_relevancy_min": 0.10,
            },
        }
        errors = validate_thresholds_nonzero(data)
        assert len(errors) >= 1
        assert "NaN" in errors[0]

    def test_threshold_file_not_found(self):
        with pytest.raises(ThresholdError, match="not found"):
            load_thresholds(Path("/nonexistent/eval_thresholds.yaml"))

    def test_load_valid_threshold_file(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w") as f:
            f.write("classifier:\n  accuracy_min: 0.55\n  macro_f1_min: 0.50\n")
            f.write("rag:\n  hit_at_5_min: 0.10\n  mrr_at_10_min: 0.10\n")
            f.write("  faithfulness_min: 0.10\n  answer_relevancy_min: 0.10\n")
            f.flush()
            data = load_thresholds(Path(f.name))
            assert data["classifier"]["accuracy_min"] == 0.55

    def test_check_threshold_pass(self):
        passed, msg = check_threshold(0.85, 0.55, "accuracy")
        assert passed
        assert ">=" in msg

    def test_check_threshold_fail(self):
        passed, msg = check_threshold(0.40, 0.55, "accuracy")
        assert not passed
        assert "<" in msg

    def test_get_classifier_threshold(self):
        data = {"classifier": {"accuracy_min": 0.55, "macro_f1_min": 0.50}}
        assert get_classifier_threshold(data, "accuracy") == 0.55

    def test_get_rag_threshold(self):
        data = {"rag": {"hit_at_5_min": 0.10}}
        assert get_rag_threshold(data, "hit_at_5") == 0.10

    def test_missing_metric_returns_zero(self):
        data = {"classifier": {}}
        assert get_classifier_threshold(data, "accuracy") == 0.0

    def test_non_numeric_threshold_fails(self):
        data = {
            "classifier": {"accuracy_min": "not-a-number", "macro_f1_min": 0.50},
            "rag": {},
        }
        errors = validate_thresholds_nonzero(data)
        assert len(errors) >= 1

    def test_disabled_thresholds_detected(self):
        """Thresholds must be enabled (non-zero). Zero effectively means disabled."""
        data = {
            "classifier": {"accuracy_min": 0.0, "macro_f1_min": 0.0},
            "rag": {
                "hit_at_5_min": 0.0,
                "mrr_at_10_min": 0.0,
                "faithfulness_min": 0.0,
                "answer_relevancy_min": 0.0,
            },
        }
        errors = validate_thresholds_nonzero(data)
        assert len(errors) >= 6

    def test_missing_rag_thresholds_fail(self):
        data = {"classifier": {"accuracy_min": 0.55, "macro_f1_min": 0.50}, "rag": {}}
        errors = validate_thresholds_nonzero(data)
        assert len(errors) >= 1
        assert any("rag" in e for e in errors)

    def test_all_thresholds_missing_fails(self):
        data = {}
        errors = validate_thresholds_nonzero(data)
        assert len(errors) >= 1

    def test_empty_yaml_file(self):
        import yaml

        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w") as f:
            f.write("")
            f.flush()
            data = load_thresholds(Path(f.name))
        assert data == {}

    def test_malformed_threshold_strictly_invalid(self):
        """Malformed YAML (None sections) should fail validation gracefully."""
        data = {"classifier": None, "rag": None}
        errors = validate_thresholds_nonzero(data)
        assert len(errors) >= 1

    def test_infinite_threshold_fails(self):
        data = {
            "classifier": {"accuracy_min": float("inf"), "macro_f1_min": 0.50},
            "rag": {},
        }
        errors = validate_thresholds_nonzero(data)
        assert len(errors) >= 1
