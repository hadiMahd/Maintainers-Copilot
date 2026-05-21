"""Unit tests for eval report schema validation."""

import json
import tempfile
from pathlib import Path

import pytest

from scripts.ci.eval_report import (
    build_report,
    determine_overall_passed,
    read_report,
    validate_report,
    write_report,
)


class TestEvalReportSchema:
    def test_build_report_has_required_fields(self):
        report = build_report(
            classifier_metrics={
                "accuracy": 0.85,
                "macro_f1": 0.80,
                "per_class_f1": {"bug": 0.85},
                "threshold": 0.55,
                "passed": True,
                "failures": [],
            },
            rag_metrics={
                "hit_at_5": 0.30,
                "mrr_at_10": 0.25,
                "faithfulness": 0.80,
                "answer_relevancy": 0.75,
                "threshold": 0.10,
                "passed": True,
                "failures": [],
            },
            storage_bucket="evals",
            storage_key="test_report.json",
        )
        required = ["run_id", "timestamp", "classifier", "rag", "storage", "passed"]
        for key in required:
            assert key in report, f"Missing {key}"

    def test_validate_report_missing_fields(self):
        report = {"run_id": "abc"}
        errors = validate_report(report)
        assert len(errors) > 0
        assert "Missing" in errors[0]

    def test_validate_report_valid(self):
        report = build_report()
        errors = validate_report(report)
        assert errors == []

    def test_write_and_read_report_roundtrip(self):
        report = build_report(run_id="test-001")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)

        try:
            write_report(report, tmp)
            loaded = read_report(tmp)
            assert loaded["run_id"] == "test-001"
            assert loaded["storage"]["bucket"] == "evals"
        finally:
            tmp.unlink(missing_ok=True)

    def test_build_report_custom_run_id(self):
        report = build_report(run_id="my-custom-id")
        assert report["run_id"] == "my-custom-id"

    def test_build_report_generates_run_id(self):
        report = build_report()
        assert len(report["run_id"]) > 0

    def test_determine_overall_passed_all_pass(self):
        report = build_report(
            classifier_metrics={
                "accuracy": 0.9,
                "macro_f1": 0.85,
                "per_class_f1": {"bug": 0.9},
                "threshold": 0.55,
                "passed": True,
                "failures": [],
            },
            rag_metrics={
                "hit_at_5": 0.5,
                "mrr_at_10": 0.4,
                "faithfulness": 0.9,
                "answer_relevancy": 0.85,
                "threshold": 0.1,
                "passed": True,
                "failures": [],
            },
        )
        assert determine_overall_passed(report) is True

    def test_determine_overall_passed_classifier_fails(self):
        report = build_report(
            classifier_metrics={
                "accuracy": 0.3,
                "macro_f1": 0.25,
                "per_class_f1": {},
                "threshold": 0.55,
                "passed": False,
                "failures": ["accuracy below threshold"],
            },
        )
        assert determine_overall_passed(report) is False

    def test_report_includes_storage_bucket_and_key(self):
        report = build_report(storage_bucket="eval-bucket", storage_key="my-key.json")
        assert report["storage"]["bucket"] == "eval-bucket"
        assert report["storage"]["key"] == "my-key.json"

    def test_schema_version_is_set(self):
        report = build_report()
        assert report["schema_version"] == "1.0"

    def test_classifier_contains_all_required_metrics(self):
        report = build_report(
            classifier_metrics={
                "accuracy": 0.85,
                "macro_f1": 0.80,
                "per_class_f1": {"bug": 0.85, "feature": 0.80},
                "threshold": 0.55,
                "passed": True,
                "failures": [],
            },
        )
        cls = report["classifier"]
        assert "accuracy" in cls
        assert "macro_f1" in cls
        assert "per_class_f1" in cls
        assert "threshold" in cls
        assert "passed" in cls
        assert isinstance(cls["per_class_f1"], dict)

    def test_rag_contains_all_required_metrics(self):
        report = build_report(
            rag_metrics={
                "hit_at_5": 0.30,
                "mrr_at_10": 0.25,
                "faithfulness": 0.80,
                "answer_relevancy": 0.75,
                "threshold": 0.10,
                "passed": True,
                "failures": [],
            },
        )
        rag = report["rag"]
        assert "hit_at_5" in rag
        assert "mrr_at_10" in rag
        assert "faithfulness" in rag
        assert "answer_relevancy" in rag
        assert "threshold" in rag
        assert "passed" in rag

    def test_all_numeric_metrics_in_range(self):
        report = build_report(
            classifier_metrics={
                "accuracy": 0.5,
                "macro_f1": 0.5,
                "per_class_f1": {"x": 0.5},
                "threshold": 0.5,
                "passed": True,
                "failures": [],
            },
            rag_metrics={
                "hit_at_5": 0.5,
                "mrr_at_10": 0.5,
                "faithfulness": 0.5,
                "answer_relevancy": 0.5,
                "threshold": 0.5,
                "passed": True,
                "failures": [],
            },
        )
        cls = report["classifier"]
        for metric in ["accuracy", "macro_f1", "threshold"]:
            assert 0.0 <= cls[metric] <= 1.0, f"{metric} out of range"
        rag = report["rag"]
        for metric in ["hit_at_5", "mrr_at_10", "faithfulness", "answer_relevancy", "threshold"]:
            assert 0.0 <= rag[metric] <= 1.0, f"{metric} out of range"

    def test_report_passed_is_boolean(self):
        report = build_report()
        assert isinstance(report["passed"], bool)

    def test_timestamp_is_iso_format(self):
        report = build_report()
        ts = report["timestamp"]
        assert "T" in ts or "+" in ts or "Z" in ts

    def test_run_id_not_empty(self):
        report = build_report()
        assert len(report["run_id"]) >= 1

    def test_storage_bucket_and_key_not_empty(self):
        report = build_report(storage_bucket="my-bucket", storage_key="my-key.json")
        assert len(report["storage"]["bucket"]) >= 1
        assert len(report["storage"]["key"]) >= 1

    def test_classifier_with_failures(self):
        report = build_report(
            classifier_metrics={
                "accuracy": 0.3,
                "macro_f1": 0.2,
                "per_class_f1": {},
                "threshold": 0.55,
                "passed": False,
                "failures": ["accuracy below threshold", "macro_f1 below threshold"],
            },
        )
        assert report["classifier"]["passed"] is False
        assert len(report["classifier"]["failures"]) == 2
