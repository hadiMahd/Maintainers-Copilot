"""RAG judge clients for deterministic CI and optional RAGAS metrics.

The token-overlap judge is deterministic, zero-dependency, and records a
stable ``judge_id`` in eval reports for CI reproducibility.

It computes unigram F1 between a candidate answer and a reference answer
as a proxy for faithfulness / answer relevancy.
"""

from __future__ import annotations

import logging
import math
import os
import uuid
from dataclasses import dataclass, field
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
        del retrieved_content
        return compute_unigram_f1(candidate_answer, question)

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


@dataclass(frozen=True)
class RagasMetricResult:
    """Aggregated RAGAS metric values for a RAG eval run."""

    context_precision: float | None = None
    context_recall: float | None = None
    context_entity_recall: float | None = None
    noise_sensitivity: float | None = None
    faithfulness: float | None = None
    response_relevancy: float | None = None
    failures: list[str] = field(default_factory=list)

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "enabled": True,
            "context_precision": self.context_precision,
            "context_recall": self.context_recall,
            "context_entity_recall": self.context_entity_recall,
            "noise_sensitivity": self.noise_sensitivity,
            "faithfulness": self.faithfulness,
            "response_relevancy": self.response_relevancy,
            "failures": list(self.failures),
        }


class RagasJudgeClient:
    """RAGAS-backed evaluator for real RAG eval runs.

    This is intentionally separate from ``TokenOverlapJudge``. The frozen judge
    remains the CI gate; RAGAS metrics are added to real eval reports when
    ``USE_RAGAS_EVALS=1``.
    """

    provider_backend = "ragas"

    def __init__(
        self,
        *,
        embeddings: Any,
        noise_llm: Any,
    ) -> None:
        self._embeddings = embeddings
        self._noise_llm = noise_llm

    async def score_batch(self, samples: list[dict[str, Any]]) -> RagasMetricResult:
        normalized = [_normalize_ragas_sample(sample) for sample in samples]
        if not normalized:
            return RagasMetricResult(failures=["No RAGAS samples were provided"])

        standard_metrics, standard_failures = await self._score_standard_metrics(normalized)
        noise_value, noise_failures = await self._score_noise_sensitivity(normalized)

        return RagasMetricResult(
            context_precision=standard_metrics.get("context_precision"),
            context_recall=standard_metrics.get("context_recall"),
            context_entity_recall=standard_metrics.get("context_entity_recall"),
            noise_sensitivity=noise_value,
            faithfulness=standard_metrics.get("faithfulness"),
            response_relevancy=standard_metrics.get("answer_relevancy"),
            failures=standard_failures + noise_failures,
        )

    async def _score_standard_metrics(
        self,
        samples: list[dict[str, Any]],
    ) -> tuple[dict[str, float | None], list[str]]:
        try:
            from ragas.metrics.collections.answer_relevancy import AnswerRelevancy
            from ragas.metrics.collections.context_entity_recall import ContextEntityRecall
            from ragas.metrics.collections.context_precision import ContextPrecisionWithReference
            from ragas.metrics.collections.context_recall import ContextRecall
            from ragas.metrics.collections.faithfulness import Faithfulness
        except ImportError as exc:
            raise RuntimeError(
                "RAGAS metrics require the rag optional dependencies "
                "(install with: uv sync --extra rag)"
            ) from exc

        context_precision = ContextPrecisionWithReference(
            llm=self._noise_llm,
            name="context_precision",
        )
        context_recall = ContextRecall(llm=self._noise_llm)
        context_entity_recall = ContextEntityRecall(llm=self._noise_llm)
        faithfulness = Faithfulness(llm=self._noise_llm)
        answer_relevancy = AnswerRelevancy(
            llm=self._noise_llm,
            embeddings=self._embeddings,
        )

        values: dict[str, list[float]] = {
            "context_precision": [],
            "context_recall": [],
            "context_entity_recall": [],
            "faithfulness": [],
            "answer_relevancy": [],
        }
        failures: list[str] = []
        for idx, sample in enumerate(samples):
            logger.info(
                "RAGAS standard metrics scoring sample",
                extra={"sample_index": idx, "sample_count": len(samples)},
            )
            metric_calls = {
                "context_precision": context_precision.ascore(
                    user_input=sample["user_input"],
                    reference=sample["reference"],
                    retrieved_contexts=sample["retrieved_contexts"],
                ),
                "context_recall": context_recall.ascore(
                    user_input=sample["user_input"],
                    retrieved_contexts=sample["retrieved_contexts"],
                    reference=sample["reference"],
                ),
                "context_entity_recall": context_entity_recall.ascore(
                    reference=sample["reference"],
                    retrieved_contexts=sample["retrieved_contexts"],
                ),
                "faithfulness": faithfulness.ascore(
                    user_input=sample["user_input"],
                    response=sample["response"],
                    retrieved_contexts=sample["retrieved_contexts"],
                ),
                "answer_relevancy": answer_relevancy.ascore(
                    user_input=sample["user_input"],
                    response=sample["response"],
                ),
            }
            for key, call in metric_calls.items():
                try:
                    result = await call
                except Exception as exc:  # pragma: no cover - depends on external judge
                    failures.append(f"RAGAS {key} failed for sample {idx}: {exc}")
                    continue
                value = _finite_float(getattr(result, "value", None))
                if value is None:
                    failures.append(f"RAGAS {key} did not produce a finite score for sample {idx}")
                    continue
                values[key].append(value)

        scores = {key: _avg_or_none(metric_values) for key, metric_values in values.items()}
        failures.extend(
            f"RAGAS metric {key} did not produce any finite scores"
            for key, value in scores.items()
            if value is None
        )
        return scores, failures

    async def _score_noise_sensitivity(
        self,
        samples: list[dict[str, Any]],
    ) -> tuple[float | None, list[str]]:
        try:
            from ragas.metrics.collections import NoiseSensitivity
        except ImportError as exc:
            raise RuntimeError(
                "RAGAS noise sensitivity requires the rag optional dependencies "
                "(install with: uv sync --extra rag)"
            ) from exc

        metric = NoiseSensitivity(llm=self._noise_llm, mode="relevant")
        values: list[float] = []
        failures: list[str] = []
        for idx, sample in enumerate(samples):
            logger.info(
                "RAGAS noise sensitivity scoring sample",
                extra={"sample_index": idx, "sample_count": len(samples)},
            )
            try:
                result = await metric.ascore(
                    user_input=sample["user_input"],
                    response=sample["response"],
                    reference=sample["reference"],
                    retrieved_contexts=sample["retrieved_contexts"],
                )
            except Exception as exc:  # pragma: no cover - depends on external judge
                failures.append(f"RAGAS noise_sensitivity failed for sample {idx}: {exc}")
                continue
            value = _finite_float(getattr(result, "value", None))
            if value is None:
                failures.append(
                    f"RAGAS noise_sensitivity did not produce a finite score for sample {idx}"
                )
                continue
            values.append(value)
        return _avg_or_none(values), failures


def _normalize_ragas_sample(sample: dict[str, Any]) -> dict[str, Any]:
    contexts = sample.get("retrieved_contexts") or []
    return {
        "user_input": str(sample.get("user_input") or sample.get("question") or ""),
        "response": str(sample.get("response") or sample.get("answer") or ""),
        "reference": str(sample.get("reference") or sample.get("expected_answer") or ""),
        "retrieved_contexts": [str(context) for context in contexts if str(context).strip()],
    }


def _average_metric(rows: list[dict[str, Any]], key: str) -> float | None:
    return _avg_or_none(
        [value for row in rows if (value := _finite_float(row.get(key))) is not None]
    )


def _avg_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _secret_value(value: object | None) -> str | None:
    if value is None:
        return None
    getter = getattr(value, "get_secret_value", None)
    if getter is not None:
        return str(getter())
    return str(value)


def resolve_ragas_judge(settings: object) -> RagasJudgeClient:
    """Resolve a RAGAS judge from Vault-backed Azure settings."""
    endpoint = (
        getattr(settings, "rag_azure_generation_endpoint", None)
        or getattr(settings, "azure_openai_endpoint", None)
        or os.environ.get("RAG_AZURE_GENERATION_ENDPOINT")
    )
    api_key = (
        getattr(settings, "rag_azure_generation_api_key", None)
        or _secret_value(getattr(settings, "azure_openai_api_key", None))
        or os.environ.get("RAG_AZURE_GENERATION_API_KEY")
    )
    model = (
        getattr(settings, "rag_azure_generation_model", None)
        or getattr(settings, "azure_openai_model", None)
        or os.environ.get("RAG_AZURE_GENERATION_MODEL")
    )
    if not endpoint or not api_key or not model:
        raise RuntimeError("RAGAS eval requires Azure generation settings")

    embedding_endpoint = (
        getattr(settings, "rag_azure_embedding_endpoint", None)
        or getattr(settings, "azure_openai_endpoint", None)
        or endpoint
    )
    embedding_api_key = (
        getattr(settings, "rag_azure_embedding_api_key", None)
        or _secret_value(getattr(settings, "azure_openai_api_key", None))
        or api_key
    )
    embedding_model = (
        getattr(settings, "azure_openai_embedding_model", None)
        or os.environ.get("AZURE_EMBEDDING_MODEL")
        or "text-embedding-3-small"
    )
    api_version = str(getattr(settings, "azure_openai_api_version", "2024-02-01"))
    timeout = int(getattr(settings, "rag_judge_timeout_seconds", 15) or 15)

    try:
        import instructor
        from openai import AsyncAzureOpenAI
        from ragas.embeddings.base import embedding_factory
        from ragas.llms.adapters.instructor import InstructorLLM, InstructorModelArgs
    except ImportError as exc:
        raise RuntimeError(
            "RAGAS eval requires llm and rag optional dependencies "
            "(install with: uv sync --extra llm --extra rag)"
        ) from exc

    noise_client = AsyncAzureOpenAI(
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version=api_version,
        timeout=timeout,
    )
    embeddings_client = AsyncAzureOpenAI(
        api_key=embedding_api_key,
        azure_endpoint=embedding_endpoint,
        api_version=api_version,
        timeout=timeout,
    )
    noise_llm = InstructorLLM(
        client=instructor.from_openai(noise_client, mode=instructor.Mode.JSON),
        model=model,
        provider="azure",
        model_args=InstructorModelArgs(),
        temperature=0,
    )
    if os.environ.get("RAGAS_AZURE_USE_MAX_COMPLETION_TOKENS", "1") != "0":
        noise_llm.model_args.pop("max_tokens", None)
        noise_llm.model_args.pop("top_p", None)
        noise_llm.model_args["temperature"] = 1.0
        noise_llm.model_args["max_completion_tokens"] = int(
            os.environ.get("RAGAS_MAX_COMPLETION_TOKENS", "4096")
        )
    embeddings = embedding_factory(
        "openai",
        model=embedding_model,
        client=embeddings_client,
        interface="modern",
    )

    return RagasJudgeClient(
        embeddings=embeddings,
        noise_llm=noise_llm,
    )


def resolve_judge() -> TokenOverlapJudge:
    return TokenOverlapJudge()


__all__ = [
    "TokenOverlapJudge",
    "RagasJudgeClient",
    "RagasMetricResult",
    "compute_unigram_f1",
    "resolve_judge",
    "resolve_ragas_judge",
    "_DEFAULT_JUDGE_ID",
]
