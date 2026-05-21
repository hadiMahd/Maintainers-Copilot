"""Eval report builder primitives matching eval-report.schema.json."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def build_report(
    run_id: Optional[str] = None,
    classifier_metrics: Optional[dict[str, Any]] = None,
    rag_metrics: Optional[dict[str, Any]] = None,
    redaction_passed: bool = True,
    redaction_summary: str = "",
    static_secret_passed: bool = True,
    static_secret_summary: str = "",
    artifact_passed: bool = True,
    artifact_summary: str = "",
    startup_passed: bool = True,
    startup_summary: str = "",
    tracing_passed: bool = True,
    tracing_summary: str = "",
    storage_bucket: str = "evals",
    storage_key: str = "",
    previous_green_available: bool = False,
    previous_green_passed: bool = True,
    previous_green_summary: str = "",
    threshold_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    rid = run_id or uuid.uuid4().hex
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": rid,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "classifier": classifier_metrics or _empty_classifier(),
        "rag": rag_metrics or _empty_rag(),
        "redaction": {
            "passed": redaction_passed,
            "summary": redaction_summary,
        },
        "static_secret_grep": {
            "passed": static_secret_passed,
            "summary": static_secret_summary,
        },
        "artifact_integrity": {
            "passed": artifact_passed,
            "summary": artifact_summary,
        },
        "startup": {
            "passed": startup_passed,
            "summary": startup_summary,
        },
        "tracing": {
            "passed": tracing_passed,
            "summary": tracing_summary,
        },
        "storage": {
            "bucket": storage_bucket,
            "key": storage_key or f"eval_report_{rid}.json",
        },
        "previous_green_comparison": {
            "available": previous_green_available,
            "previous_report_uri": None,
            "passed": previous_green_passed,
            "summary": previous_green_summary,
            "regressions": [],
        },
        "passed": True,
    }

    if threshold_data:
        report["thresholds"] = threshold_data

    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = ["run_id", "timestamp", "classifier", "rag", "storage", "passed"]
    for key in required:
        if key not in report:
            errors.append(f"Missing required field: {key}")
    return errors


def write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(report, f, indent=2)


def read_report(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def determine_overall_passed(report: dict[str, Any]) -> bool:
    classifier_passed = report.get("classifier", {}).get("passed", True)
    rag_passed = report.get("rag", {}).get("passed", True)
    redaction_passed = report.get("redaction", {}).get("passed", True)
    static_passed = report.get("static_secret_grep", {}).get("passed", True)
    artifact_passed = report.get("artifact_integrity", {}).get("passed", True)
    startup_passed = report.get("startup", {}).get("passed", True)
    tracing_passed = report.get("tracing", {}).get("passed", True)
    prev_passed = report.get("previous_green_comparison", {}).get("passed", True)
    return all([
        classifier_passed, rag_passed, redaction_passed, static_passed,
        artifact_passed, startup_passed, tracing_passed, prev_passed,
    ])


def _empty_classifier() -> dict[str, Any]:
    return {
        "accuracy": 0.0,
        "macro_f1": 0.0,
        "per_class_f1": {},
        "threshold": 0.0,
        "passed": False,
        "failures": [],
    }


def _empty_rag() -> dict[str, Any]:
    return {
        "hit_at_5": 0.0,
        "mrr_at_10": 0.0,
        "faithfulness": 0.0,
        "answer_relevancy": 0.0,
        "threshold": 0.0,
        "passed": False,
        "failures": [],
    }
