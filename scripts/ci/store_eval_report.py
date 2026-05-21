"""Store eval report in MinIO (or local fallback for dev/test)."""

from pathlib import Path
from scripts.ci.common import fail, pass_gate
from scripts.ci.report_storage import store_report


if __name__ == "__main__":
    current_path = Path("evals/reports/eval_report.json")
    if not current_path.exists():
        fail("Report storage: no current eval report found")

    from scripts.ci.eval_report import read_report
    report = read_report(current_path)
    bucket = report.get("storage", {}).get("bucket", "evals")
    key = report.get("storage", {}).get("key", "eval_report_latest.json")

    ok = store_report(report, bucket, key)
    if not ok:
        fail(f"Report storage: failed to store {key}")
    pass_gate(f"Report storage: stored {key} (local fallback)")
