"""Contract tests for RAG service contracts — retrieval result schemas and grounded answers."""

from __future__ import annotations

import pytest

from app.domain.rag import (
    GroundedAnswer,
    RAGChunk,
    RAGGenerationError,
    RAGInsufficientEvidenceError,
    RAGRetrievalError,
    RetrievalQuery,
    RetrievalResult,
    RetrievalResultSet,
)


class TestRetrievalResultSchema:
    def test_retrieval_result_has_required_fields(self):
        chunk = RAGChunk(
            chunk_id="c1",
            parent_id="p1",
            source_type="docs",
            content="test content",
            content_hash="abc123",
            token_count=2,
        )
        result = RetrievalResult(rank=1, final_score=0.9, chunk=chunk)
        assert result.rank == 1
        assert result.final_score == 0.9
        assert result.chunk.chunk_id == "c1"

    def test_retrieval_result_optional_scores(self):
        chunk = RAGChunk(
            chunk_id="c1",
            parent_id="p1",
            source_type="docs",
            content="test",
            content_hash="abc",
            token_count=1,
        )
        result = RetrievalResult(
            rank=1,
            final_score=0.9,
            chunk=chunk,
            sparse_score=0.5,
            dense_score=0.8,
            rerank_score=0.95,
        )
        assert result.sparse_score == 0.5
        assert result.dense_score == 0.8
        assert result.rerank_score == 0.95

    def test_retrieval_result_set_holds_mode(self):
        result_set = RetrievalResultSet(results=[])
        assert result_set.results == []
        assert result_set.retrieval_mode == "hybrid"


class TestGroundedAnswerSchema:
    def test_grounded_answer_requires_answer(self):
        with pytest.raises(Exception):
            GroundedAnswer(answer="")

    def test_grounded_answer_insufficient_evidence(self):
        answer = GroundedAnswer(
            answer="Cannot answer",
            insufficient_evidence=True,
            limitations=["No evidence found"],
        )
        assert answer.insufficient_evidence
        assert answer.limitations == ["No evidence found"]
        assert answer.supporting_chunk_ids == []

    def test_grounded_answer_with_supporting_chunks(self):
        answer = GroundedAnswer(
            answer="The issue is resolved by installing numpy.",
            supporting_chunk_ids=["c1", "c2"],
            insufficient_evidence=False,
        )
        assert len(answer.supporting_chunk_ids) == 2
        assert not answer.insufficient_evidence


class TestRetrievalQuerySchema:
    def test_minimal_query(self):
        q = RetrievalQuery(query="how to install numpy")
        assert q.query == "how to install numpy"
        assert q.retrieval_mode == "hybrid"
        assert q.top_k == 5

    def test_query_with_metadata_filters(self):
        q = RetrievalQuery(
            query="fix error",
            metadata_filters={"source_type": "docs"},
            embedding_model="all-MiniLM-L6-v2",
        )
        assert q.metadata_filters["source_type"] == "docs"

    def test_query_modes(self):
        for mode in ("sparse", "dense", "hybrid"):
            q = RetrievalQuery(query="test", retrieval_mode=mode)
            assert q.retrieval_mode == mode


class TestDomainExceptions:
    def test_retrieval_error(self):
        err = RAGRetrievalError("store unavailable", details={"store": "pgvector"})
        assert err.error_code == "RAG_RETRIEVAL_ERROR"
        assert "store unavailable" in str(err)
        assert err.details["store"] == "pgvector"

    def test_generation_error(self):
        err = RAGGenerationError("timeout")
        assert err.error_code == "RAG_GENERATION_ERROR"

    def test_insufficient_evidence_error(self):
        err = RAGInsufficientEvidenceError("not enough context")
        assert err.error_code == "RAG_INSUFFICIENT_EVIDENCE"
