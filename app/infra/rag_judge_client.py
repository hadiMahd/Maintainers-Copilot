"""RAG judge client — frozen token-overlap scorer for CI generation metrics.

The token-overlap judge is deterministic, zero-dependency, and records a
stable ``judge_id`` in eval reports for CI reproducibility.

It computes unigram F1 between a candidate answer and a reference answer
as a proxy for faithfulness / answer relevancy.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)

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
        combined = f"{question} {retrieved_content}"
        return compute_unigram_f1(candidate_answer, combined)

    def judge_batch(
        self,
        *,
        questions: list[str],
        candidate_answers: list[str],
        reference_answers: list[str],
        retrieved_contents: list[str] | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> list[dict[str, Any]]:
        rid = request_id or uuid.uuid4().hex
        tid = trace_id or uuid.uuid4().hex
        scores: list[dict[str, Any]] = []
        for i in range(len(questions)):
            faith = self.score_faithfulness(candidate_answers[i], reference_answers[i])
            rel = self.score_answer_relevancy(
                candidate_answers[i],
                questions[i],
                retrieved_contents[i] if retrieved_contents else "",
            )
            scores.append(
                {
                    "index": i,
                    "faithfulness": faith,
                    "answer_relevancy": rel,
                }
            )
        logger.info(
            "Judge batch complete",
            extra={
                "request_id": rid,
                "trace_id": tid,
                "judge_id": self._judge_id,
                "examples_judged": len(scores),
            },
        )
        return scores


class NonCIJudgeStub:
    """Config seam for optional RAGAS-style non-CI judging.

    Raises ``NotImplementedError`` — real RAGAS metrics are out of scope
    for US2 and are wired separately when the optional dependency is present.
    """

    def __init__(self, model: str = "ragas") -> None:
        self._model = model

    @property
    def provider_backend(self) -> str:
        return "ragas-stub"

    def judge(self, *, question: str, answer: str, context: str) -> dict:
        raise NotImplementedError("RAGAS-style judging is not implemented in this pass")


def resolve_judge() -> TokenOverlapJudge:
    return TokenOverlapJudge()


def resolve_non_ci_judge() -> NonCIJudgeStub:
    return NonCIJudgeStub()


__all__ = [
    "TokenOverlapJudge",
    "NonCIJudgeStub",
    "compute_unigram_f1",
    "resolve_judge",
    "resolve_non_ci_judge",
    "_DEFAULT_JUDGE_ID",
]
