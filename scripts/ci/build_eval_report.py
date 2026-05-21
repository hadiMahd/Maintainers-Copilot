"""Build combined eval_report.json from classifier and RAG eval results."""

import json
import os
from pathlib import Path

from scripts.ci.common import fail, pass_gate
from scripts.ci.eval_report import build_report, determine_overall_passed, write_report
from scripts.ci.thresholds import load_thresholds

if __name__ == "__main__":
    classifier_result_path = Path("evals/reports/classifier_result.json")
    rag_result_path = Path("evals/reports/rag_result.json")

    classifier_metrics = None
    rag_metrics = None

    if classifier_result_path.exists():
        with open(classifier_result_path) as f:
            classifier_raw = json.load(f)
        classifier_metrics = {
            "accuracy": classifier_raw.get("accuracy", 0.0),
            "macro_f1": classifier_raw.get("macro_f1", 0.0),
            "per_class_f1": classifier_raw.get("per_class_f1", {}),
            "threshold": 0.55,
            "passed": classifier_raw.get("passed", True),
            "failures": classifier_raw.get("failures", []),
        }

    if rag_result_path.exists():
        with open(rag_result_path) as f:
            rag_raw = json.load(f)
        rag_metrics = {
            "hit_at_5": rag_raw.get("hit_at_5", 0.0),
            "mrr_at_10": rag_raw.get("mrr_at_10", 0.0),
            "faithfulness": rag_raw.get("faithfulness", 0.0),
            "answer_relevancy": rag_raw.get("answer_relevancy", 0.0),
            "threshold": 0.10,
            "passed": rag_raw.get("passed", True),
            "failures": rag_raw.get("failures", []),
        }

    threshold_data = load_thresholds()

    report = build_report(
        run_id=os.environ.get("CI_RUN_ID"),
        classifier_metrics=classifier_metrics,
        rag_metrics=rag_metrics,
        threshold_data=threshold_data,
        storage_bucket="evals",
        storage_key="eval_report_latest.json",
    )

    report["passed"] = determine_overall_passed(report)

    out = Path("evals/reports/eval_report.json")
    write_report(report, out)
    print(f"Eval report written: {out}")
    print(f"Overall passed: {report['passed']}")

    if not report["passed"]:
        fail("Build eval report: overall evaluation FAILED")
    pass_gate("Eval report: built and valid")
