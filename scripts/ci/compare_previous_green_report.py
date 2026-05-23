"""Compare current eval report against previous green build.

Uses 2 absolute percentage point regression threshold.
Fails if any tracked metric drops by more than 2pp from previous green.
"""

from pathlib import Path

from scripts.ci.common import fail, pass_gate
from scripts.ci.eval_report import read_report
from scripts.ci.report_storage import find_previous_green_report

REGRESSION_THRESHOLD = 0.02


if __name__ == "__main__":
    current_path = Path("evals/reports/eval_report.json")
    if not current_path.exists():
        fail("Previous green diff: no current eval report found")

    prev = find_previous_green_report("evals")
    if prev is None:
        pass_gate("Previous green diff: no previous green report (first run)")

    current = read_report(current_path)

    regressions: list[str] = []
    classifier_cur = current.get("classifier", {})
    classifier_prev = prev.get("classifier", {}) if prev else {}
    rag_cur = current.get("rag", {})
    rag_prev = prev.get("rag", {}) if prev else {}

    for metric in ["accuracy", "macro_f1"]:
        cur_val = classifier_cur.get(metric, 0.0)
        prev_val = classifier_prev.get(metric, 0.0)
        if prev_val - cur_val > REGRESSION_THRESHOLD:
            regressions.append(
                f"classifier.{metric}: {prev_val:.4f} -> {cur_val:.4f} (drop: {prev_val - cur_val:.4f})"
            )

    for metric in ["hit_at_5", "mrr_at_10", "faithfulness", "answer_relevancy"]:
        cur_val = rag_cur.get(metric, 0.0)
        prev_val = rag_prev.get(metric, 0.0)
        if prev_val - cur_val > REGRESSION_THRESHOLD:
            regressions.append(
                f"rag.{metric}: {prev_val:.4f} -> {cur_val:.4f} (drop: {prev_val - cur_val:.4f})"
            )

    if regressions:
        fail(
            f"Previous green diff: {len(regressions)} regression(s) > "
            f"{REGRESSION_THRESHOLD*100:.0f}pp: {'; '.join(regressions)}"
        )
    pass_gate(f"Previous green diff: no regressions > {REGRESSION_THRESHOLD*100:.0f}pp")
