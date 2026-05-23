"""RAG index service — chunk-to-embedding orchestration, duplicate detection, sparse search prep."""

from __future__ import annotations

import logging
import uuid

from app.domain.rag import RAGChunk, RAGEmbedding
from app.infra.embedding_client import BaseEmbeddingClient
from app.repositories.rag_embedding_repository import RAGEmbeddingRepository

logger = logging.getLogger(__name__)


class RAGIndexService:
    """Orchestrate chunk indexing: embedding generation, sparse search, duplicate skipping."""

    def __init__(
        self,
        embedding_client: BaseEmbeddingClient,
        embedding_repo: RAGEmbeddingRepository | None = None,
    ) -> None:
        self._embedding_client = embedding_client
        self._embedding_repo = embedding_repo

    def embed_chunks(self, chunks: list[RAGChunk]) -> list[RAGEmbedding]:
        texts = [c.content for c in chunks]
        vectors = self._embedding_client.encode(texts)
        embeddings: list[RAGEmbedding] = []
        for chunk, vector in zip(chunks, vectors):
            embeddings.append(
                RAGEmbedding(
                    embedding_id=uuid.uuid4().hex,
                    chunk_id=chunk.chunk_id,
                    content_hash=chunk.content_hash,
                    embedding_model=self._embedding_client.model_name,
                    embedding_dim=len(vector),
                    vector=list(vector),
                )
            )
        logger.info(
            "Generated %d embeddings for model %s",
            len(embeddings),
            self._embedding_client.model_name,
        )
        return embeddings

    def filter_duplicate_embeddings(
        self,
        embeddings: list[RAGEmbedding],
        existing_hashes: set[str] | None = None,
    ) -> list[RAGEmbedding]:
        seen: set[str] = set(existing_hashes or [])
        deduped: list[RAGEmbedding] = []
        skipped = 0
        for emb in embeddings:
            key = f"{emb.content_hash}:{emb.embedding_model}"
            if key in seen:
                skipped += 1
                continue
            seen.add(key)
            deduped.append(emb)
        if skipped:
            logger.info("Skipped %d duplicate embeddings", skipped)
        return deduped

    def build_embedding_comparison(
        self,
        local_embedded: int,
        local_total: int,
    ) -> dict:
        return {
            "all-MiniLM-L6-v2": {
                "dim": self._embedding_client.dim,
                "chunks_embedded": local_embedded,
                "chunks_total": local_total,
                "status": "completed",
            },
            "text-embedding-3-small": {
                "dim": 1536,
                "chunks_embedded": 0,
                "chunks_total": 0,
                "status": "unavailable",
                "note": "Azure embedding requires real credentials; use fake path in tests",
            },
        }


__all__ = ["RAGIndexService"]
