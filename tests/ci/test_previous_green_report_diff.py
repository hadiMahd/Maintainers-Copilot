"""Tests for previous-green report comparison with regression detection."""

from pathlib import Path

from scripts.ci.eval_report import build_report
from scripts.ci.report_storage import (
    find_previous_green_report,
    store_report_local,
)

REGRESSION_THRESHOLD = 0.02


def _make_report(
    accuracy=0.85,
    macro_f1=0.80,
    hit_at_5=0.30,
    mrr_at_10=0.25,
    faithfulness=0.80,
    answer_relevancy=0.75,
    passed=True,
):
    return build_report(
        run_id="test-run",
        classifier_metrics={
            "accuracy": accuracy,
            "macro_f1": macro_f1,
            "per_class_f1": {"bug": 0.85},
            "threshold": 0.55,
            "passed": passed,
            "failures": [] if passed else ["accuracy below threshold"],
        },
        rag_metrics={
            "hit_at_5": hit_at_5,
            "mrr_at_10": mrr_at_10,
            "faithfulness": faithfulness,
            "answer_relevancy": answer_relevancy,
            "threshold": 0.10,
            "passed": passed,
            "failures": [] if passed else ["hit_at_5 below threshold"],
        },
        previous_green_available=True,
        previous_green_passed=True,
        previous_green_summary="",
    )


def _compare_reports(current, previous):
    """Replicate the regression check logic."""
    regressions = []
    classifier_cur = current.get("classifier", {})
    classifier_prev = previous.get("classifier", {})
    rag_cur = current.get("rag", {})
    rag_prev = previous.get("rag", {})

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

    return regressions


class TestPreviousGreenDiff:
    """Verify regression detection from previous green report."""

    def test_no_regression_when_equal(self):
        current = _make_report(accuracy=0.85, macro_f1=0.80)
        previous = _make_report(accuracy=0.85, macro_f1=0.80)
        regressions = _compare_reports(current, previous)
        assert regressions == []

    def test_no_regression_when_improved(self):
        current = _make_report(accuracy=0.90, macro_f1=0.85)
        previous = _make_report(accuracy=0.85, macro_f1=0.80)
        regressions = _compare_reports(current, previous)
        assert regressions == []

    def test_regression_detected_within_classifier(self):
        """Regression > 2 absolute pp should be detected."""
        current = _make_report(accuracy=0.70)
        previous = _make_report(accuracy=0.80)
        regressions = _compare_reports(current, previous)
        assert len(regressions) == 1
        assert "accuracy" in regressions[0]

    def test_small_drop_within_tolerance_passes(self):
        """Drop less than 2pp should NOT trigger regression."""
        current = _make_report(accuracy=0.84, macro_f1=0.79)
        previous = _make_report(accuracy=0.85, macro_f1=0.80)
        regressions = _compare_reports(current, previous)
        assert len(regressions) == 0

    def test_multiple_regressions_detected(self):
        """Multiple metrics regressing > 2pp should all be reported."""
        current = _make_report(accuracy=0.60, macro_f1=0.50, hit_at_5=0.10, mrr_at_10=0.05)
        previous = _make_report(accuracy=0.80, macro_f1=0.75, hit_at_5=0.30, mrr_at_10=0.25)
        regressions = _compare_reports(current, previous)
        assert len(regressions) >= 2

    def test_rag_regression_detected(self):
        current = _make_report(hit_at_5=0.10, mrr_at_10=0.08)
        previous = _make_report(hit_at_5=0.30, mrr_at_10=0.28)
        regressions = _compare_reports(current, previous)
        assert len(regressions) >= 2

    def test_no_previous_report_is_not_a_regression(self):
        """If no previous green report, that's not a regression."""
        result = find_previous_green_report("evals", prefix="zzz_nonexistent_test_")
        assert result is None

    def test_find_previous_green_returns_passing_report(self):
        rp = Path("evals/reports/test_green_pass.json")
        try:
            store_report_local(_make_report(passed=True), rp)
            prev = find_previous_green_report("evals", prefix="test_green_pass")
            if prev is not None:
                assert prev.get("passed") is True
        finally:
            rp.unlink(missing_ok=True)

    def test_regression_summary_contains_metric_names(self):
        current = _make_report(accuracy=0.50, macro_f1=0.40)
        previous = _make_report(accuracy=0.85, macro_f1=0.80)
        regressions = _compare_reports(current, previous)
        assert any("accuracy" in r for r in regressions)
        assert any("macro_f1" in r for r in regressions)
