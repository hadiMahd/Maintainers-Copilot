"""Unit tests for sparse/dense score normalization and weighted hybrid ranking."""

from __future__ import annotations

import pytest


class TestScoreNormalization:
    def test_sparse_scores_normalized_to_0_1(self):
        raw_scores = [0.05, 0.0, 0.1, 0.01, 0.001]
        norm = _normalize_scores(raw_scores)
        assert all(0.0 <= s <= 1.0 for s in norm)
        # max value (0.1 at index 2) → 1.0
        assert norm[2] == pytest.approx(1.0)
        # min value (0.0 at index 1) → 0.0
        assert norm[1] == pytest.approx(0.0)

    def test_single_score_normalizes_to_1(self):
        assert _normalize_scores([0.5]) == [1.0]

    def test_all_same_scores_normalize_to_1(self):
        norm = _normalize_scores([0.3, 0.3, 0.3])
        assert all(s == 1.0 for s in norm)

    def test_dense_scores_minus_1_to_1_normalized(self):
        raw = [0.8, 0.5, -0.2, 0.3]
        norm = _normalize_scores(raw)
        # After normalization, max→1.0, min→0.0
        assert norm[raw.index(max(raw))] == pytest.approx(1.0)
        assert norm[raw.index(min(raw))] == pytest.approx(0.0)

    def test_empty_scores_returns_empty(self):
        assert _normalize_scores([]) == []


class TestHybridWeighting:
    def test_weighted_combination(self):
        sparse = [1.0, 0.5, 0.0]
        dense = [0.8, 1.0, 0.3]
        combined = _weighted_hybrid(sparse, dense, sparse_weight=0.3, dense_weight=0.7)
        # After normalization: sparse stays [1.0, 0.5, 0.0],
        # dense becomes [(0.8-0.3)/(1-0.3)=0.714, 1.0, 0.0]
        assert len(combined) == 3
        assert combined[0] == pytest.approx(0.3 * 1.0 + 0.7 * 0.714, abs=0.01)
        assert combined[1] == pytest.approx(0.3 * 0.5 + 0.7 * 1.0, abs=0.01)
        assert combined[2] == pytest.approx(0.3 * 0.0 + 0.7 * 0.0, abs=0.01)

    def test_different_lengths_pad_correctly(self):
        sparse = [1.0, 0.5]
        dense = [0.8]
        combined = _weighted_hybrid(sparse, dense, sparse_weight=0.5, dense_weight=0.5)
        # max_len = 2, combined = [s0+d0, s1+0]
        assert len(combined) == 2

    def test_hybrid_ordering_respects_weights(self):
        sparse = [0.9, 0.1]
        dense = [0.2, 0.95]
        combined = _weighted_hybrid(sparse, dense, sparse_weight=0.8, dense_weight=0.2)
        assert combined[0] > combined[1]

    def test_final_score_is_probabilistic_range(self):
        combined = _weighted_hybrid([1.0, 0.5], [0.8, 1.0], 0.4, 0.6)
        assert all(0.0 <= s <= 1.0 for s in combined)


class TestCosineToScore:
    def test_cosine_1_is_max(self):
        assert _cosine_to_score(1.0) == 1.0

    def test_cosine_minus_1_is_0(self):
        assert _cosine_to_score(-1.0) == 0.0

    def test_cosine_0_is_midpoint(self):
        assert _cosine_to_score(0.0) == 0.5

    def test_cosine_out_of_range_clamped(self):
        assert 0.0 <= _cosine_to_score(2.0) <= 1.0


# -- Helpers (mirror retrieval service logic) ---------------------------------


def _normalize_scores(scores: list[float]) -> list[float]:
    if not scores:
        return []
    mn, mx = min(scores), max(scores)
    if mx == mn:
        return [1.0] * len(scores)
    return [(s - mn) / (mx - mn) for s in scores]


def _cosine_to_score(cosine: float) -> float:
    return max(0.0, min(1.0, (cosine + 1.0) / 2.0))


def _weighted_hybrid(
    sparse_scores: list[float],
    dense_scores: list[float],
    sparse_weight: float,
    dense_weight: float,
) -> list[float]:
    norm_sparse = _normalize_scores(sparse_scores)
    norm_dense = _normalize_scores(dense_scores)
    max_len = max(len(norm_sparse), len(norm_dense))
    combined = []
    for i in range(max_len):
        s = norm_sparse[i] if i < len(norm_sparse) else 0.0
        d = norm_dense[i] if i < len(norm_dense) else 0.0
        combined.append(sparse_weight * s + dense_weight * d)
    return combined
