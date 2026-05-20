"""RAG judge client — frozen token-overlap scorer for CI generation metrics.

The token-overlap judge is deterministic, zero-dependency, and records a
stable ``judge_id`` in eval reports for CI reproducibility.

It computes unigram F1 between a candidate answer and a reference answer
as a proxy for faithfulness / answer relevancy.
"""

from __future__ import annotations

import uuid
from typing import Any


_DEFAULT_JUDGE_ID = "token-overlap-f1-v1"


def tokenize(text: str) -> set[str]:
    return set(text.lower().split())


def compute_unigram_f1(candidate: str, reference: str) -> float:
    candidate_tokens = tokenize(candidate)
    reference_tokens = tokenize(reference)
    if not candidate_tokens or not reference_tokens:
        return 0.0
    intersection = candidate_tokens & reference_tokens
    precision = len(intersection) / len(candidate_tokens)
    recall = len(intersection) / len(reference_tokens)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


class TokenOverlapJudge:
    """Frozen CI judge for faithfulness and answer relevancy.

    Uses token-overlap (unigram F1) to compare candidate answers against
    reference answers. Records a stable ``judge_id`` for eval reports.
    """

    def __init__(self, judge_id: str = _DEFAULT_JUDGE_ID) -> None:
        self._judge_id = judge_id

    @property
    def judge_id(self) -> str:
        return self._judge_id

    def score_faithfulness(self, candidate_answer: str, reference_answer: str) -> float:
        return compute_unigram_f1(candidate_answer, reference_answer)

    def score_answer_relevancy(
        self,
        candidate_answer: str,
        question: str,
        retrieved_content: str,
    ) -> float:
        """
        Simple token-overlap relevancy score between candidate answer and the
        combined question + retrieved content.  This is a deterministic proxy;
        not a semantic similarity metric.
        """
        combined = f"{question} {retrieved_content}"
        return compute_unigram_f1(candidate_answer, combined)


def resolve_judge() -> TokenOverlapJudge:
    return TokenOverlapJudge()


__all__ = [
    "TokenOverlapJudge",
    "compute_unigram_f1",
    "resolve_judge",
    "_DEFAULT_JUDGE_ID",
]
