"""Build combined eval_report.json from classifier and RAG results."""

from pathlib import Path
from scripts.ci.common import fail, pass_gate
from scripts.ci.eval_report import build_report, write_report


if __name__ == "__main__":
    report = build_report(storage_bucket="evals", storage_key="eval_report_latest.json")
    out = Path("evals/reports/eval_report.json")
    write_report(report, out)
    print(f"Eval report written: {out}")
    pass_gate("Eval report: built and written (stub - full build in US2)")
