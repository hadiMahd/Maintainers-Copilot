"""RAG chunk repository — sparse, dense, and hybrid search operations."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.rag import RAGChunk, RAGRetrievalError, RetrievalResult

logger = logging.getLogger(__name__)

_DENSE_SEARCH_SQL = """
SELECT
    c.chunk_id, c.parent_id, c.source_type, c.source_path, c.issue_number,
    c.source_url, c.title, c.labels, c.created_at, c.updated_at,
    c.chunk_index, c.content, c.content_hash, c.token_count, c.metadata,
    1.0 - (e.vector <=> query_c.vector) AS dense_score
FROM rag_chunks c
JOIN rag_embeddings e ON e.chunk_id = c.chunk_id
CROSS JOIN (SELECT vector::vector AS vector FROM rag_embeddings WHERE chunk_id = :query_chunk_id LIMIT 1) query_c
WHERE e.embedding_model = :embedding_model
ORDER BY e.vector <=> query_c.vector
LIMIT :top_k
"""

_SPARSE_SEARCH_SQL = """
SELECT
    c.chunk_id, c.parent_id, c.source_type, c.source_path, c.issue_number,
    c.source_url, c.title, c.labels, c.created_at, c.updated_at,
    c.chunk_index, c.content, c.content_hash, c.token_count, c.metadata,
    ts_rank(s.search_vector, plainto_tsquery('english', :query_text)) AS sparse_score
FROM rag_chunks c
JOIN rag_sparse_search s ON s.chunk_id = c.chunk_id
WHERE s.search_vector @@ plainto_tsquery('english', :query_text)
ORDER BY sparse_score DESC
LIMIT :top_k
"""


class RAGChunkRepository:
    """Async repository for RAG chunk search and retrieval."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, chunk_id: str) -> RAGChunk | None:
        result = await self._session.execute(
            text("SELECT * FROM rag_chunks WHERE chunk_id = :chunk_id"),
            {"chunk_id": chunk_id},
        )
        row = result.mappings().first()
        if row is None:
            return None
        return _row_to_chunk(row)

    async def search_dense(
        self,
        query_text: str,
        embedding_model: str,
        top_k: int = 10,
    ) -> list[RetrievalResult]:
        rows = await self._session.execute(
            text(_DENSE_SEARCH_SQL),
            {"query_text": query_text, "embedding_model": embedding_model, "top_k": top_k},
        )
        results: list[RetrievalResult] = []
        for idx, row in enumerate(rows.mappings(), start=1):
            chunk = _row_to_chunk(dict(row))
            results.append(RetrievalResult(
                rank=idx,
                final_score=float(row.get("dense_score", 0.0)),
                chunk=chunk,
                content_preview=chunk.content[:200],
                dense_score=float(row.get("dense_score", 0.0)),
                retrieval_mode="dense",
            ))
        return results

    async def search_sparse(
        self,
        query_text: str,
        top_k: int = 10,
    ) -> list[RetrievalResult]:
        rows = await self._session.execute(
            text(_SPARSE_SEARCH_SQL),
            {"query_text": query_text, "top_k": top_k},
        )
        results: list[RetrievalResult] = []
        for idx, row in enumerate(rows.mappings(), start=1):
            chunk = _row_to_chunk(dict(row))
            results.append(RetrievalResult(
                rank=idx,
                final_score=float(row.get("sparse_score", 0.0)),
                chunk=chunk,
                content_preview=chunk.content[:200],
                sparse_score=float(row.get("sparse_score", 0.0)),
                retrieval_mode="sparse",
            ))
        return results

    async def search_hybrid(
        self,
        query_text: str,
        embedding_model: str,
        sparse_weight: float = 0.3,
        dense_weight: float = 0.7,
        top_k: int = 10,
    ) -> list[RetrievalResult]:
        dense_results = await self.search_dense(query_text, embedding_model, top_k * 2)
        sparse_results = await self.search_sparse(query_text, top_k * 2)
        return _merge_hybrid(dense_results, sparse_results, sparse_weight, dense_weight, top_k)


def _row_to_chunk(row: dict) -> RAGChunk:
    return RAGChunk(
        chunk_id=str(row["chunk_id"]),
        parent_id=str(row["parent_id"]),
        source_type=row["source_type"],
        source_path=row.get("source_path"),
        issue_number=row.get("issue_number"),
        source_url=row.get("source_url"),
        title=row.get("title"),
        labels=list(row["labels"]) if row.get("labels") else [],
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        chunk_index=int(row.get("chunk_index", 0)),
        content=row.get("content", ""),
        content_hash=str(row.get("content_hash", "")),
        token_count=int(row.get("token_count", 0)),
        metadata=dict(row["metadata"]) if row.get("metadata") else {},
    )


def _merge_hybrid(
    dense: list[RetrievalResult],
    sparse: list[RetrievalResult],
    sparse_weight: float,
    dense_weight: float,
    top_k: int,
) -> list[RetrievalResult]:
    scored: dict[str, RetrievalResult] = {}
    for r in dense:
        key = r.chunk.chunk_id
        if key not in scored:
            scored[key] = r
            r.final_score = (r.dense_score or 0.0) * dense_weight
    for r in sparse:
        key = r.chunk.chunk_id
        if key in scored:
            scored[key].final_score += (r.sparse_score or 0.0) * sparse_weight
            scored[key].sparse_score = r.sparse_score
            scored[key].retrieval_mode = "hybrid"
        else:
            r.final_score = (r.sparse_score or 0.0) * sparse_weight
            r.retrieval_mode = "hybrid"
            scored[key] = r
    merged = sorted(scored.values(), key=lambda x: x.final_score, reverse=True)
    for idx, r in enumerate(merged[:top_k], start=1):
        r.rank = idx
    return merged[:top_k]


__all__ = ["RAGChunkRepository"]
