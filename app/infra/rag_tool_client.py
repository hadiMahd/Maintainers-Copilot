"""Project-owned RAG tool client seam."""

from __future__ import annotations

import logging

from app.domain.chat_tools import (
    AnswerProjectQuestionInput,
    RAGRetrievedChunk,
    RAGToolClientResponse,
    ToolSourceReference,
)
from app.domain.rag import RetrievalQuery, RetrievalResultSet

logger = logging.getLogger(__name__)


class BaseRAGToolClient:
    """Abstract RAG tool seam used by chat orchestration."""

    async def answer_project_question(
        self,
        payload: AnswerProjectQuestionInput,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> RAGToolClientResponse:
        raise NotImplementedError


class FakeRAGToolClient(BaseRAGToolClient):
    """Deterministic RAG tool fake for tests."""

    def __init__(self, result: RAGToolClientResponse | None = None) -> None:
        self._result = result or RAGToolClientResponse(
            answer="Grounded answer from fake retrieval.",
            supporting_sources=[],
            limitations=[],
            retrieval_trace_id="rag-trace-001",
            retrieved_chunks=[],
        )

    async def answer_project_question(
        self,
        payload: AnswerProjectQuestionInput,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> RAGToolClientResponse:
        _ = (payload, request_id, trace_id)
        return self._result


class RAGToolClient(BaseRAGToolClient):
    """Real RAG tool client wrapping retrieval and generation services."""

    def __init__(
        self,
        *,
        session_factory,
        generation_client,
        settings,
    ) -> None:
        self._session_factory = session_factory
        self._generation_client = generation_client
        self._settings = settings

    async def answer_project_question(
        self,
        payload: AnswerProjectQuestionInput,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> RAGToolClientResponse:
        from app.infra.embedding_client import resolve_embedding_client
        from app.infra.reranker_client import resolve_reranker
        from app.repositories.rag_chunk_repository import RAGChunkRepository
        from app.services.rag_generation_service import RAGGenerationService
        from app.services.rag_retrieval_service import RAGRetrievalService

        embedding_client = resolve_embedding_client(self._settings)
        query = RetrievalQuery(
            query=payload.question,
            metadata_filters=payload.metadata_filters,
            retrieval_mode="hybrid",
            embedding_model=embedding_client.model_name,
            query_transformation_enabled=True,
            reranking_enabled=True,
            top_k=5,
        )
        try:
            async with self._session_factory() as session:
                repo = RAGChunkRepository(session)
                retrieval_service = RAGRetrievalService(
                    repo,
                    sparse_weight=self._settings.rag_hybrid_sparse_weight,
                    dense_weight=self._settings.rag_hybrid_dense_weight,
                    reranker=resolve_reranker(self._settings),
                    embedding_client=embedding_client,
                )
                result_set: RetrievalResultSet = await retrieval_service.retrieve(
                    query,
                    request_id=request_id,
                    trace_id=trace_id,
                )
        except Exception as exc:
            logger.warning("RAG retrieval failed: %s", exc)
            return RAGToolClientResponse(
                answer="Retrieval failed. Please try again later.",
                supporting_sources=[],
                limitations=[f"Retrieval error: {exc}"],
                retrieval_trace_id=trace_id,
                retrieved_chunks=[],
            )

        try:
            generation_service = RAGGenerationService(self._generation_client)
            grounded = await generation_service.generate(
                question=payload.question,
                retrieved=result_set,
                request_id=request_id,
                trace_id=trace_id,
            )
        except Exception as exc:
            logger.warning("RAG generation failed: %s", exc)
            return RAGToolClientResponse(
                answer="Answer generation failed. Please try again later.",
                supporting_sources=[],
                limitations=[f"Generation error: {exc}"],
                retrieval_trace_id=trace_id,
                retrieved_chunks=[],
            )

        chunks = [
            RAGRetrievedChunk(
                chunk_id=r.chunk.chunk_id,
                source_path=r.chunk.source_path,
                score=r.final_score,
                preview=r.chunk.content[:200],
            )
            for r in result_set.results[:5]
        ]
        return RAGToolClientResponse(
            answer=grounded.answer,
            supporting_sources=[
                ToolSourceReference(
                    source_id=r.chunk.chunk_id,
                    source_path=r.chunk.source_path,
                    score=r.final_score,
                )
                for r in result_set.results[:5]
            ],
            limitations=grounded.limitations or [],
            retrieval_trace_id=trace_id,
            retrieved_chunks=chunks,
        )
