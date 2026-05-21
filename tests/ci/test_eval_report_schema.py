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
