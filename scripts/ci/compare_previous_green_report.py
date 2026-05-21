"""Compare current eval report against previous green build."""

from pathlib import Path
from scripts.ci.common import fail, pass_gate
from scripts.ci.report_storage import find_previous_green_report, load_report_local


REGRESSION_THRESHOLD = 0.02  # 2 absolute percentage points


if __name__ == "__main__":
    current_path = Path("evals/reports/eval_report.json")
    if not current_path.exists():
        fail("Previous green diff: no current eval report found")

    prev = find_previous_green_report("evals")
    if prev is None:
        pass_gate("Previous green diff: no previous green report (first run)")
        exit(0)

    current = load_report_local(current_path)

    regressions: list[str] = []
    classifier_cur = current.get("classifier", {})
    classifier_prev = prev.get("classifier", {})
    rag_cur = current.get("rag", {})
    rag_prev = prev.get("rag", {})

    for metric in ["accuracy", "macro_f1"]:
        cur_val = classifier_cur.get(metric, 0.0)
        prev_val = classifier_prev.get(metric, 0.0)
        if prev_val - cur_val > REGRESSION_THRESHOLD:
            regressions.append(f"classifier.{metric}: {prev_val:.3f} -> {cur_val:.3f}")

    for metric in ["hit_at_5", "mrr_at_10", "faithfulness", "answer_relevancy"]:
        cur_val = rag_cur.get(metric, 0.0)
        prev_val = rag_prev.get(metric, 0.0)
        if prev_val - cur_val > REGRESSION_THRESHOLD:
            regressions.append(f"rag.{metric}: {prev_val:.3f} -> {cur_val:.3f}")

    if regressions:
        fail(f"Previous green diff: {len(regressions)} regression(s): {'; '.join(regressions)}")
    pass_gate("Previous green diff: no regressions (stub - full check in US2)")
