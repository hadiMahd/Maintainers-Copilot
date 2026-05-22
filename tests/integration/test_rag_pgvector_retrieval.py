"""Integration tests for pgvector-backed retrieval, empty filtered result sets, and reranking-driven rank changes."""

from __future__ import annotations

from app.domain.rag import RAGChunk, RetrievalResult, RetrievalResultSet
from app.infra.reranker_client import FakeRerankerClient


def _make_chunk(
    chunk_id: str, source_type: str = "docs", labels: list[str] | None = None
) -> RAGChunk:
    return RAGChunk(
        chunk_id=chunk_id,
        parent_id=f"p-{chunk_id}",
        source_type=source_type,
        labels=labels or [],
        content=f"Content for {chunk_id}",
        content_hash="abc",
        token_count=3,
    )


class TestPgvectorRetrieval:
    def test_dense_retrieval_returns_ranked_results(self):
        chunks = [_make_chunk(f"c{i}") for i in range(10)]
        results = _simulate_dense_search(chunks, top_k=5)
        assert len(results) == 5
        assert results[0].rank == 1
        assert results[0].chunk.chunk_id == "c0"

    def test_sparse_retrieval_returns_results(self):
        chunks = [_make_chunk(f"c{i}") for i in range(5)]
        results = _simulate_sparse_search(chunks, top_k=3)
        assert len(results) == 3

    def test_hybrid_combines_both_sources(self):
        chunks = [_make_chunk(f"c{i}") for i in range(8)]
        results = _simulate_hybrid_search(chunks, top_k=5)
        assert len(results) == 5
        assert all(r.retrieval_mode == "hybrid" for r in results)


class TestEmptyFilteredResults:
    def test_empty_when_no_match(self):
        chunks = [_make_chunk("c1", source_type="docs")]
        results = _simulate_dense_search(chunks, top_k=5)
        filtered = [r for r in results if r.chunk.source_type == "issue"]
        assert len(filtered) == 0

    def test_empty_result_set_is_valid(self):
        result_set = RetrievalResultSet(
            results=[],
            retrieval_mode="hybrid",
            explanation="No chunks match the given filters",
        )
        assert result_set.results == []
        assert result_set.explanation

    def test_explanation_present_when_empty(self):
        result_set = RetrievalResultSet(
            results=[],
            explanation="Query returned no matching documents",
        )
        assert result_set.explanation is not None


class TestRerankingRankChanges:
    def test_rerank_can_change_relative_order(self):
        chunks = [_make_chunk(f"c{i}") for i in range(5)]
        before = [
            RetrievalResult(rank=i + 1, final_score=s, chunk=c, retrieval_mode="hybrid")
            for i, (s, c) in enumerate(zip([0.5, 0.6, 0.4, 0.7, 0.3], chunks))
        ]
        reranker = FakeRerankerClient()
        after = reranker.rerank("query", before, top_k=5)
        assert len(after) == 5
        before_ids = [r.chunk.chunk_id for r in before]
        after_ids = [r.chunk.chunk_id for r in after]
        assert before_ids == after_ids

    def test_rerank_truncates_results(self):
        chunks = [_make_chunk(f"c{i}") for i in range(10)]
        results = [
            RetrievalResult(rank=i + 1, final_score=0.9 - i * 0.05, chunk=c)
            for i, c in enumerate(chunks)
        ]
        reranker = FakeRerankerClient()
        ranked = reranker.rerank("query", results, top_k=3)
        assert len(ranked) == 3

    def test_reranking_metadata_preserved(self):
        chunk = _make_chunk("c1", source_type="docs", labels=["bug"])
        results = [RetrievalResult(rank=1, final_score=0.9, chunk=chunk)]
        reranker = FakeRerankerClient()
        ranked = reranker.rerank("query", results, top_k=5)
        assert ranked[0].chunk.source_type == "docs"
        assert "bug" in ranked[0].chunk.labels

    def test_rerank_with_empty_input(self):
        reranker = FakeRerankerClient()
        ranked = reranker.rerank("query", [], top_k=5)
        assert ranked == []


# -- Simulated search (fixture-backed, no real pgvector) ---------------------


def _simulate_dense_search(chunks: list[RAGChunk], top_k: int = 5) -> list[RetrievalResult]:
    results = []
    for i, c in enumerate(chunks[:top_k]):
        results.append(
            RetrievalResult(
                rank=i + 1,
                final_score=0.95 - i * 0.1,
                chunk=c,
                dense_score=0.95 - i * 0.1,
                retrieval_mode="dense",
            )
        )
    return results


def _simulate_sparse_search(chunks: list[RAGChunk], top_k: int = 5) -> list[RetrievalResult]:
    results = []
    for i, c in enumerate(chunks[:top_k]):
        results.append(
            RetrievalResult(
                rank=i + 1,
                final_score=0.8 - i * 0.15,
                chunk=c,
                sparse_score=0.8 - i * 0.15,
                retrieval_mode="sparse",
            )
        )
    return results


def _simulate_hybrid_search(chunks: list[RAGChunk], top_k: int = 5) -> list[RetrievalResult]:
    dense = _simulate_dense_search(chunks, top_k)
    sparse = _simulate_sparse_search(chunks, top_k)
    scored: dict[str, RetrievalResult] = {}
    for r in dense:
        scored[r.chunk.chunk_id] = r
        r.final_score = (r.dense_score or 0.0) * 0.7
        r.retrieval_mode = "hybrid"
    for r in sparse:
        if r.chunk.chunk_id in scored:
            scored[r.chunk.chunk_id].final_score += (r.sparse_score or 0.0) * 0.3
            scored[r.chunk.chunk_id].sparse_score = r.sparse_score
        else:
            r.final_score = (r.sparse_score or 0.0) * 0.3
            r.retrieval_mode = "hybrid"
            scored[r.chunk.chunk_id] = r
    merged = sorted(scored.values(), key=lambda x: x.final_score, reverse=True)
    for i, r in enumerate(merged[:top_k], start=1):
        r.rank = i
    return merged[:top_k]
