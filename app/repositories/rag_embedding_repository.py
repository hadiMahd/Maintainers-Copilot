"""RAG embedding repository — lookup and upsert operations."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.rag import RAGEmbedding

logger = logging.getLogger(__name__)


class RAGEmbeddingRepository:
    """Async repository for RAG embedding lookup and upsert."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_chunk_id(self, chunk_id: str, embedding_model: str) -> RAGEmbedding | None:
        result = await self._session.execute(
            text(
                "SELECT * FROM rag_embeddings "
                "WHERE chunk_id = :chunk_id AND embedding_model = :embedding_model"
            ),
            {"chunk_id": chunk_id, "embedding_model": embedding_model},
        )
        row = result.mappings().first()
        if row is None:
            return None
        return _row_to_embedding(row)

    async def upsert(self, embedding: RAGEmbedding) -> RAGEmbedding:
        existing = await self.get_by_chunk_id(embedding.chunk_id, embedding.embedding_model)
        if existing is not None:
            await self._session.execute(
                text(
                    "UPDATE rag_embeddings SET content_hash = :content_hash, "
                    "vector = :vector, embedding_dim = :embedding_dim "
                    "WHERE chunk_id = :chunk_id AND embedding_model = :embedding_model"
                ),
                {
                    "content_hash": embedding.content_hash,
                    "vector": embedding.vector,
                    "embedding_dim": embedding.embedding_dim,
                    "chunk_id": embedding.chunk_id,
                    "embedding_model": embedding.embedding_model,
                },
            )
        else:
            await self._session.execute(
                text(
                    "INSERT INTO rag_embeddings "
                    "(embedding_id, chunk_id, content_hash, embedding_model, embedding_dim, vector) "
                    "VALUES (:embedding_id, :chunk_id, :content_hash, :embedding_model, "
                    ":embedding_dim, :vector)"
                ),
                {
                    "embedding_id": embedding.embedding_id,
                    "chunk_id": embedding.chunk_id,
                    "content_hash": embedding.content_hash,
                    "embedding_model": embedding.embedding_model,
                    "embedding_dim": embedding.embedding_dim,
                    "vector": embedding.vector,
                },
            )
        return embedding


def _row_to_embedding(row) -> RAGEmbedding:
    vec = row.get("vector")
    if vec is not None and not isinstance(vec, list):
        vec = list(vec)
    return RAGEmbedding(
        embedding_id=str(row["embedding_id"]),
        chunk_id=str(row["chunk_id"]),
        content_hash=str(row["content_hash"]),
        embedding_model=row["embedding_model"],
        embedding_dim=int(row["embedding_dim"]),
        vector=vec or [],
        created_at=row.get("created_at"),
    )


__all__ = ["RAGEmbeddingRepository"]
