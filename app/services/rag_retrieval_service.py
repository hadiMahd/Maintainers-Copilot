"""RAG retrieval service — sparse, dense, and hybrid retrieval orchestration."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from app.domain.rag import (
    RetrievalQuery,
    RetrievalResult,
    RetrievalResultSet,
    RAGRetrievalError,
)
from app.infra.redaction import redact_chunk_preview
from app.repositories.rag_chunk_repository import RAGChunkRepository

logger = logging.getLogger(__name__)


class RAGRetrievalService:
    def __init__(
        self,
        repo: RAGChunkRepository,
        *,
        sparse_weight: float = 0.3,
        dense_weight: float = 0.7,
    ) -> None:
        self._repo = repo
        self._sparse_weight = sparse_weight
        self._dense_weight = dense_weight

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
            if query.retrieval_mode == "sparse":
                results = await self._repo.search_sparse(query.query, query.top_k)
                return RetrievalResultSet(
                    results=results,
                    retrieval_mode="sparse",
                    request_id=rid,
                )
            if query.retrieval_mode == "dense":
                if not query.embedding_model:
                    raise RAGRetrievalError("embedding_model is required for dense retrieval")
                results = await self._repo.search_dense(
                    query.query, query.embedding_model, query.top_k
                )
                return RetrievalResultSet(
                    results=results,
                    retrieval_mode="dense",
                    request_id=rid,
                )
            if not query.embedding_model:
                raise RAGRetrievalError("embedding_model is required for hybrid retrieval")
            results = await self._repo.search_hybrid(
                query.query,
                query.embedding_model,
                sparse_weight=self._sparse_weight,
                dense_weight=self._dense_weight,
                top_k=query.top_k,
            )
            return RetrievalResultSet(
                results=results,
                retrieval_mode="hybrid",
                request_id=rid,
            )
        except RAGRetrievalError:
            raise
        except Exception as exc:
            logger.warning("Retrieval failed", extra={"request_id": rid, "trace_id": tid})
            raise RAGRetrievalError(f"Retrieval failed: {exc}") from exc


__all__ = ["RAGRetrievalService"]
