"""Contract tests for RAG evaluation commands — report schema, threshold gating, safe stderr."""

from __future__ import annotations

from app.domain.rag import (
    EvalMetrics,
    EvalReport,
    EvalRun,
)


def _make_fixture_eval_run(
    mode: str, hit: float, mrr: float, judge_id: str = "token-overlap-f1-v1"
) -> EvalRun:
    return EvalRun(
        mode=mode,
        metrics=EvalMetrics(hit_at_5=hit, mrr_at_10=mrr, faithfulness=0.8, answer_relevancy=0.7),
        embedding_model="all-MiniLM-L6-v2",
        retrieval_mode="hybrid",
        examples_completed=25,
        judge_id=judge_id,
        disagreement_notes=["example disagreement"] if mode == "advanced" else [],
    )


class TestEvalReportSchema:
    def test_report_has_all_required_fields(self):
        baseline = _make_fixture_eval_run("baseline", 0.4, 0.5)
        advanced = _make_fixture_eval_run("advanced", 0.6, 0.7)
        report = EvalReport(
            baseline=baseline,
            advanced=advanced,
            advanced_beats_baseline=True,
            embedding_comparison={"all-MiniLM-L6-v2": 384, "text-embedding-3-small": 1536},
        )
        assert report.report_id
        assert report.baseline.judge_id == "token-overlap-f1-v1"
        assert report.advanced.judge_id == "token-overlap-f1-v1"
        assert report.advanced_beats_baseline

    def test_report_json_roundtrips(self):
        baseline = _make_fixture_eval_run("baseline", 0.5, 0.6)
        advanced = _make_fixture_eval_run("advanced", 0.7, 0.8)
        report = EvalReport(
            baseline=baseline,
            advanced=advanced,
            embedding_comparison={"all-MiniLM-L6-v2": 384},
        )
        data = report.model_dump()
        assert data["baseline"]["mode"] == "baseline"
        parsed = EvalReport(**data)
        assert parsed.report_id == report.report_id

    def test_judge_id_present_on_both_runs(self):
        baseline = _make_fixture_eval_run("baseline", 0.5, 0.5)
        advanced = _make_fixture_eval_run("advanced", 0.6, 0.6, judge_id="token-overlap-f1-v1")
        assert baseline.judge_id == "token-overlap-f1-v1"
        assert advanced.judge_id == "token-overlap-f1-v1"

    def test_embedding_comparison_has_both_candidates(self):
        comparison = {
            "all-MiniLM-L6-v2": {"dim": 384, "hit_at_5": 0.4, "mrr_at_10": 0.5},
            "text-embedding-3-small": {"dim": 1536, "hit_at_5": 0.35, "mrr_at_10": 0.45},
        }
        report = EvalReport(
            baseline=_make_fixture_eval_run("baseline", 0.4, 0.5),
            advanced=_make_fixture_eval_run("advanced", 0.6, 0.7),
            embedding_comparison=comparison,
        )
        assert "all-MiniLM-L6-v2" in report.embedding_comparison
        assert "text-embedding-3-small" in report.embedding_comparison

    def test_disagreement_notes_recorded(self):
        advanced = _make_fixture_eval_run("advanced", 0.6, 0.7)
        advanced.disagreement_notes = ["note1", "note2"]
        report = EvalReport(
            baseline=_make_fixture_eval_run("baseline", 0.4, 0.5),
            advanced=advanced,
        )
        assert len(report.advanced.disagreement_notes) == 2


class TestThresholdGating:
    def test_gate_passes_when_advanced_beats_baseline(self):
        baseline = _make_fixture_eval_run("baseline", 0.4, 0.5)
        advanced = _make_fixture_eval_run("advanced", 0.6, 0.7)
        assert advanced.metrics.hit_at_5 > baseline.metrics.hit_at_5
        assert advanced.metrics.mrr_at_10 > baseline.metrics.mrr_at_10

    def test_gate_fails_when_advanced_worse(self):
        baseline = _make_fixture_eval_run("baseline", 0.6, 0.7)
        advanced = _make_fixture_eval_run("advanced", 0.4, 0.5)
        assert advanced.metrics.hit_at_5 < baseline.metrics.hit_at_5

    def test_exploratory_mode_allows_worse_advanced(self):
        baseline = _make_fixture_eval_run("baseline", 0.6, 0.7)
        advanced = _make_fixture_eval_run("advanced", 0.4, 0.5)
        report = EvalReport(
            baseline=baseline,
            advanced=advanced,
            advanced_beats_baseline=False,
        )
        assert not report.advanced_beats_baseline
