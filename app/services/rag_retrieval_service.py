"""RAG retrieval service — sparse, dense, and hybrid retrieval with score normalization, metadata filtering, query transformation, and reranker integration."""

from __future__ import annotations

import logging
import uuid

from app.domain.rag import (
    RAGRetrievalError,
    RetrievalQuery,
    RetrievalResult,
    RetrievalResultSet,
)
from app.infra.reranker_client import BaseRerankerClient, FakeRerankerClient
from app.repositories.rag_chunk_repository import RAGChunkRepository

logger = logging.getLogger(__name__)


def _normalize_scores(scores: list[float]) -> list[float]:
    if not scores:
        return []
    mn, mx = min(scores), max(scores)
    if mx == mn:
        return [1.0] * len(scores)
    return [(s - mn) / (mx - mn) for s in scores]


def _normalize_hybrid_merge(
    dense_results: list[RetrievalResult],
    sparse_results: list[RetrievalResult],
    sparse_weight: float,
    dense_weight: float,
) -> dict[str, RetrievalResult]:
    scored: dict[str, RetrievalResult] = {}
    d_scores = _normalize_scores([r.dense_score or 0.0 for r in dense_results])
    s_scores = _normalize_scores([r.sparse_score or 0.0 for r in sparse_results])
    for r, ns in zip(dense_results, d_scores):
        r.dense_score = ns
        scored[r.chunk.chunk_id] = r
        r.final_score = ns * dense_weight
        r.retrieval_mode = "hybrid"
    for r, ns in zip(sparse_results, s_scores):
        r.sparse_score = ns
        if r.chunk.chunk_id in scored:
            scored[r.chunk.chunk_id].final_score += ns * sparse_weight
            scored[r.chunk.chunk_id].sparse_score = ns
        else:
            r.final_score = ns * sparse_weight
            r.retrieval_mode = "hybrid"
            scored[r.chunk.chunk_id] = r
    return scored


def _apply_metadata_filters(
    results: list[RetrievalResult],
    filters: dict,
) -> list[RetrievalResult]:
    if not filters:
        return results
    filtered = []
    for r in results:
        match = True
        if "source_type" in filters:
            if r.chunk.source_type != filters["source_type"]:
                match = False
        if "source_path" in filters and match:
            if r.chunk.source_path != filters["source_path"]:
                match = False
        if "labels" in filters and match:
            target = filters["labels"]
            if isinstance(target, list) and target:
                if not any(lbl in r.chunk.labels for lbl in target):
                    match = False
        if match:
            filtered.append(r)
    return filtered


class RAGRetrievalService:
    def __init__(
        self,
        repo: RAGChunkRepository,
        *,
        sparse_weight: float = 0.3,
        dense_weight: float = 0.7,
        reranker: BaseRerankerClient | None = None,
    ) -> None:
        self._repo = repo
        self._sparse_weight = sparse_weight
        self._dense_weight = dense_weight
        self._reranker = reranker or FakeRerankerClient()

    async def retrieve(
        self,
        query: RetrievalQuery,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> RetrievalResultSet:
        rid = request_id or uuid.uuid4().hex
        tid = trace_id or uuid.uuid4().hex
        try:
            q_text = query.query
            if query.query_transformation_enabled:
                q_text = _transform_query(query.query)

            results: list[RetrievalResult]
            mode_explanation: str | None = None

            if query.retrieval_mode == "sparse":
                results = await self._repo.search_sparse(q_text, query.top_k)
                mode = "sparse"
            elif query.retrieval_mode == "dense":
                if not query.embedding_model:
                    raise RAGRetrievalError("embedding_model is required for dense retrieval")
                results = await self._repo.search_dense(q_text, query.embedding_model, query.top_k)
                mode = "dense"
            else:
                if not query.embedding_model:
                    raise RAGRetrievalError("embedding_model is required for hybrid retrieval")
                dense_results = await self._repo.search_dense(
                    q_text,
                    query.embedding_model,
                    query.top_k * 2,
                )
                sparse_results = await self._repo.search_sparse(q_text, query.top_k * 2)
                scored = _normalize_hybrid_merge(
                    dense_results,
                    sparse_results,
                    self._sparse_weight,
                    self._dense_weight,
                )
                results = sorted(scored.values(), key=lambda x: x.final_score, reverse=True)
                results = results[: query.top_k]
                mode = "hybrid"

            for idx, r in enumerate(results, start=1):
                r.rank = idx

            if query.metadata_filters:
                results = _apply_metadata_filters(results, query.metadata_filters)

            if query.reranking_enabled and results:
                results = self._reranker.rerank(query.query, results, query.top_k)

            if not results:
                mode_explanation = "No results match the query and filters"

            return RetrievalResultSet(
                results=results,
                retrieval_mode=mode,
                query_transformation_applied=query.query_transformation_enabled,
                reranking_applied=query.reranking_enabled,
                explanation=mode_explanation,
                request_id=rid,
            )
        except RAGRetrievalError:
            raise
        except Exception as exc:
            logger.warning(
                "Retrieval failed",
                extra={"request_id": rid, "trace_id": tid, "error": str(exc)},
            )
            raise RAGRetrievalError(f"Retrieval failed: {exc}") from exc


def _transform_query(query: str) -> str:
    terms = {
        "fix": "troubleshooting resolution bug fix",
        "install": "installation setup pip venv",
        "error": "error exception failure debugging",
        "numpy": "numpy array numerical computation",
        "build": "build compile cmake make",
        "pip": "pip python package installer",
        "parser": "parser tokenizer syntax parse",
        "docker": "docker container image compose",
        "test": "test pytest unittest coverage",
        "deploy": "deploy production release docker compose",
        "config": "configuration settings environment config",
        "log": "logging log_level structlog format",
        "db": "database postgresql connection query",
        "redis": "redis cache memory store",
    }
    parts = query.lower().split()
    additions = []
    seen = set()
    for word in parts:
        if word in terms and word not in seen:
            seen.add(word)
            additions.append(terms[word])
    if additions:
        return f"{query} ({' '.join(additions)})"
    return query


__all__ = [
    "RAGRetrievalService",
    "_apply_metadata_filters",
    "_transform_query",
    "_normalize_hybrid_merge",
]
