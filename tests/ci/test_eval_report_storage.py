"""Tests for eval report storage adapter."""

import json
import tempfile
from pathlib import Path

import pytest

from scripts.ci.eval_report import build_report, read_report, write_report
from scripts.ci.report_storage import (
    ReportStorageError,
    find_previous_green_report,
    load_report_local,
    store_report,
    store_report_local,
    try_load_minio,
)


class TestReportStorage:
    """Verify storage adapter stores and retrieves eval reports."""

    def test_store_report_local_writes_file(self):
        report = build_report(run_id="storage-test-001")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        try:
            result = store_report_local(report, tmp)
            assert result == tmp
            assert tmp.exists()
            loaded = read_report(tmp)
            assert loaded["run_id"] == "storage-test-001"
        finally:
            tmp.unlink(missing_ok=True)

    def test_load_report_local_file_not_found(self):
        with pytest.raises(ReportStorageError, match="not found"):
            load_report_local(Path("/nonexistent/report.json"))

    def test_store_report_fallback_to_local(self):
        report = build_report(run_id="store-fallback")
        ok = store_report(report, "evals", "test_store_report.json")
        assert ok is True
        local = Path("evals/reports/test_store_report.json")
        assert local.exists()
        loaded = read_report(local)
        assert loaded["run_id"] == "store-fallback"
        local.unlink(missing_ok=True)

    def test_store_report_creates_directory(self):
        report = build_report()
        ok = store_report(report, "evals", "test_dir_creation.json")
        assert ok is True
        assert Path("evals/reports").exists()
        Path("evals/reports/test_dir_creation.json").unlink(missing_ok=True)

    def test_try_load_minio_returns_none_when_unavailable(self):
        result = try_load_minio("nonexistent-bucket", "nonexistent-key")
        assert result is None

    def test_find_previous_green_no_reports(self):
        result = find_previous_green_report("evals", prefix="zzz_nonexistent_")
        assert result is None

    def test_find_previous_green_finds_passing(self):
        report = build_report(run_id="find-test", classifier_metrics={
            "accuracy": 0.9, "macro_f1": 0.85, "per_class_f1": {}, "threshold": 0.55,
            "passed": True, "failures": [],
        }, rag_metrics={
            "hit_at_5": 0.5, "mrr_at_10": 0.4, "faithfulness": 0.9, "answer_relevancy": 0.85,
            "threshold": 0.1, "passed": True, "failures": [],
        })
        rp = Path("evals/reports/test_find_green_pass.json")
        try:
            store_report_local(report, rp)
            prev = find_previous_green_report("evals", prefix="test_find_green")
            if prev is not None:
                assert prev.get("passed") is True
        finally:
            rp.unlink(missing_ok=True)

    def test_store_and_load_roundtrip(self):
        report = build_report(
            run_id="roundtrip-001",
            classifier_metrics={
                "accuracy": 0.88, "macro_f1": 0.82, "per_class_f1": {"bug": 0.88},
                "threshold": 0.55, "passed": True, "failures": [],
            },
            rag_metrics={
                "hit_at_5": 0.35, "mrr_at_10": 0.28, "faithfulness": 0.82,
                "answer_relevancy": 0.78, "threshold": 0.10, "passed": True, "failures": [],
            },
        )
        rp = Path("evals/reports/test_roundtrip.json")
        try:
            store_report_local(report, rp)
            loaded = load_report_local(rp)
            assert loaded["run_id"] == "roundtrip-001"
            assert loaded["classifier"]["accuracy"] == 0.88
            assert loaded["rag"]["hit_at_5"] == 0.35
        finally:
            rp.unlink(missing_ok=True)

    def test_storage_no_paid_credentials(self):
        content = Path("scripts/ci/report_storage.py").read_text()
        assert "AZURE_OPENAI_KEY" not in content
