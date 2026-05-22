"""Unit tests for RAG eval metrics: hit@5, MRR@10, token-overlap judging, latency aggregation."""

from __future__ import annotations

import pytest

from app.infra.rag_judge_client import (
    _DEFAULT_JUDGE_ID,
    TokenOverlapJudge,
    compute_unigram_f1,
)


class TestTokenOverlapJudge:
    def test_faithfulness_perfect_match(self):
        judge = TokenOverlapJudge()
        score = judge.score_faithfulness("install numpy with pip", "install numpy with pip")
        assert score == 1.0

    def test_faithfulness_partial_match(self):
        judge = TokenOverlapJudge()
        score = judge.score_faithfulness(
            "install numpy using pip package manager",
            "install numpy with pip",
        )
        assert 0.0 < score < 1.0

    def test_faithfulness_no_overlap(self):
        judge = TokenOverlapJudge()
        score = judge.score_faithfulness("configure redis", "install numpy")
        assert score == 0.0

    def test_answer_relevancy(self):
        judge = TokenOverlapJudge()
        score = judge.score_answer_relevancy(
            "install numpy",
            "how to install numpy",
            "pip install numpy pandas",
        )
        assert 0.0 < score <= 1.0

    def test_answer_relevancy_not_diluted_by_long_context(self):
        judge = TokenOverlapJudge()
        score = judge.score_answer_relevancy(
            "install numpy with pip",
            "how to install numpy",
            " ".join(f"irrelevant-{i}" for i in range(1000)),
        )
        assert score > 0.3

    def test_judge_id_stable(self):
        judge = TokenOverlapJudge()
        assert judge.judge_id == _DEFAULT_JUDGE_ID

    def test_custom_judge_id(self):
        judge = TokenOverlapJudge(judge_id="my-custom-judge-v2")
        assert judge.judge_id == "my-custom-judge-v2"


class TestUnigramF1:
    def test_exact_match(self):
        assert compute_unigram_f1("hello world", "hello world") == 1.0

    def test_no_match(self):
        assert compute_unigram_f1("hello", "world") == 0.0

    def test_empty_input(self):
        assert compute_unigram_f1("", "hello") == 0.0
        assert compute_unigram_f1("hello", "") == 0.0

    def test_partial_overlap(self):
        score = compute_unigram_f1("hello world foo", "hello world bar")
        assert 0.0 < score < 1.0


class TestHitAt5:
    def test_hit_when_expected_in_top_5(self):
        results = [
            {"chunk_id": "a"},
            {"chunk_id": "b"},
            {"chunk_id": "c"},
            {"chunk_id": "d"},
            {"chunk_id": "e"},
        ]
        hit = _compute_hit_at_5(results, ["c"])
        assert hit == 1.0

    def test_miss_when_expected_not_found(self):
        results = [{"chunk_id": "a"}, {"chunk_id": "b"}]
        hit = _compute_hit_at_5(results, ["x"])
        assert hit == 0.0

    def test_hit_with_multiple_expected(self):
        results = [
            {"chunk_id": "a"},
            {"chunk_id": "b"},
            {"chunk_id": "c"},
            {"chunk_id": "d"},
            {"chunk_id": "e"},
        ]
        hit = _compute_hit_at_5(results, ["b", "z"])
        assert hit == 1.0

    def test_aggregate_hit_at_5(self):
        examples = [
            (0, [{"chunk_id": "a"}, {"chunk_id": "b"}], ["a"]),
            (1, [{"chunk_id": "x"}, {"chunk_id": "y"}], ["a"]),
            (2, [{"chunk_id": "c"}, {"chunk_id": "d"}], ["d"]),
            (3, [{"chunk_id": "e"}], ["f"]),
        ]
        total = _aggregate_hit_at_5(examples)
        assert total == 0.5


class TestMRR:
    def test_mrr_rank_1(self):
        results = [{"chunk_id": "a"}, {"chunk_id": "b"}]
        mrr = _compute_mrr_at_10(results, ["a"])
        assert mrr == 1.0

    def test_mrr_rank_3(self):
        results = [
            {"chunk_id": "x"},
            {"chunk_id": "y"},
            {"chunk_id": "a"},
            {"chunk_id": "z"},
        ]
        mrr = _compute_mrr_at_10(results, ["a"])
        assert mrr == pytest.approx(1.0 / 3.0)

    def test_mrr_not_found(self):
        results = [{"chunk_id": "a"}, {"chunk_id": "b"}]
        mrr = _compute_mrr_at_10(results, ["x"])
        assert mrr == 0.0

    def test_mrr_aggregate(self):
        examples = [
            (0, [{"chunk_id": "a"}, {"chunk_id": "b"}], ["a"]),
            (1, [{"chunk_id": "x"}, {"chunk_id": "a"}], ["a"]),
            (2, [{"chunk_id": "y"}], ["a"]),
        ]
        total = _aggregate_mrr_at_10(examples)
        expected = (1.0 + 0.5 + 0.0) / 3.0
        assert total == pytest.approx(expected)


class TestLatencyAggregation:
    def test_p50(self):
        latencies = [10.0, 20.0, 30.0, 40.0, 50.0]
        p50 = _percentile(sorted(latencies), 50)
        assert p50 == 30.0

    def test_p95(self):
        latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        p95 = _percentile(sorted(latencies), 95)
        assert p95 == pytest.approx(95.5)

    def test_empty_latencies(self):
        p50 = _percentile([], 50)
        assert p50 == 0.0


# -- Helper implementations (mirror the eval service logic) -------------------


def _compute_hit_at_5(results: list[dict], expected_chunks: list[str]) -> float:
    for r in results[:5]:
        if r["chunk_id"] in expected_chunks:
            return 1.0
    return 0.0


def _aggregate_hit_at_5(
    examples: list[tuple[int, list[dict], list[str]]],
) -> float:
    if not examples:
        return 0.0
    hits = sum(_compute_hit_at_5(results, expected) for _, results, expected in examples)
    return hits / len(examples)


def _compute_mrr_at_10(results: list[dict], expected_chunks: list[str]) -> float:
    for i, r in enumerate(results[:10], start=1):
        if r["chunk_id"] in expected_chunks:
            return 1.0 / i
    return 0.0


def _aggregate_mrr_at_10(
    examples: list[tuple[int, list[dict], list[str]]],
) -> float:
    if not examples:
        return 0.0
    total = sum(_compute_mrr_at_10(results, expected) for _, results, expected in examples)
    return total / len(examples)


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    k = (p / 100.0) * (len(sorted_vals) - 1)
    f = int(k)
    c = k - f
    if f + 1 < len(sorted_vals):
        return sorted_vals[f] + c * (sorted_vals[f + 1] - sorted_vals[f])
    return sorted_vals[f]
