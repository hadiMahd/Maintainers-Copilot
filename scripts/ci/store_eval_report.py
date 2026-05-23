"""Store eval report in MinIO (local fallback for dev/test).

In CI with MinIO available, stores to configured bucket.
In local/dev/test mode, writes to evals/reports/ as local adapter.
"""

from pathlib import Path

from scripts.ci.common import fail, pass_gate
from scripts.ci.eval_report import read_report
from scripts.ci.report_storage import store_report

if __name__ == "__main__":
    current_path = Path("evals/reports/eval_report.json")
    if not current_path.exists():
        fail("Report storage: no current eval report found")

    report = read_report(current_path)
    bucket = report.get("storage", {}).get("bucket", "evals")
    key = report.get("storage", {}).get("key", "eval_report_latest.json")

    ok = store_report(report, bucket, key)
    if not ok:
        fail(f"Report storage: failed to store {key} to {bucket}")
    pass_gate(f"Report storage: stored {key} (bucket: {bucket})")
