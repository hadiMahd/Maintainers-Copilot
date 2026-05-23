"""RAG index building command.

Builds or updates sparse and dense retrieval indexes for the RAG corpus.
Generates embeddings using local all-MiniLM-L6-v2 (default) or optional
Azure text-embedding-3-small when configured.

Outputs:
  - artifacts/rag/embedding_comparison.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os

from app.core.config import AppSettings
from app.core.lifespan import _apply_optional_provider_settings
from app.domain.rag import RAGChunk
from app.infra.embedding_client import (
    FakeEmbeddingClient,
    resolve_embedding_client,
)
from app.services.rag_index_service import RAGIndexService

logger = logging.getLogger(__name__)

_DEFAULT_CHUNKS_PATH = "data/processed/rag_chunks.jsonl"
_DEFAULT_COMPARISON_OUTPUT = "artifacts/rag/embedding_comparison.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build RAG index from chunk corpus")
    parser.add_argument("--chunks", default=_DEFAULT_CHUNKS_PATH, help="Path to chunks JSONL")
    parser.add_argument(
        "--output", default=_DEFAULT_COMPARISON_OUTPUT, help="Path to comparison output JSON"
    )
    parser.add_argument(
        "--fake", action="store_true", help="Use fake embedding client (for testing)"
    )
    parser.add_argument(
        "--persist-db",
        action="store_true",
        help="Persist chunks, sparse rows, and embeddings into Postgres after indexing",
    )
    return parser.parse_args(argv)


def _load_chunks(path: str) -> list[RAGChunk]:
    chunks: list[RAGChunk] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            chunks.append(RAGChunk(**data))
    logger.info("Loaded %d chunks from %s", len(chunks), path)
    return chunks


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not os.path.isfile(args.chunks):
        logger.warning("Chunks file not found: %s", args.chunks)
        return 1

    chunks = _load_chunks(args.chunks)
    if not chunks:
        logger.warning("No chunks to index")
        return 0

    if args.fake:
        client = FakeEmbeddingClient()
        logger.info("Using fake embedding client for testing")
    else:
        settings = _load_settings_with_provider_secrets()
        client = resolve_embedding_client(settings)

    service = RAGIndexService(embedding_client=client)
    embeddings = service.embed_chunks(chunks)
    deduped = service.filter_duplicate_embeddings(embeddings)

    comparison = service.build_embedding_comparison(
        local_embedded=len(deduped),
        local_total=len(chunks),
    )

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(comparison, f, indent=2)
    if args.persist_db:
        database_url = _resolve_database_url()
        asyncio.run(_persist_index(database_url, chunks, deduped))
    logger.info(
        "Embedding comparison saved to %s: local=%d/%d",
        args.output,
        len(deduped),
        len(chunks),
    )
    return 0


def _resolve_database_url() -> str:
    database_url = os.environ.get("APP_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if database_url:
        return database_url

    settings = AppSettings()
    from app.infra.vault_client import fetch_secrets, init_vault_client

    vault_client = init_vault_client(settings)
    secrets = fetch_secrets(
        vault_client,
        settings.vault_secret_mount,
        settings.vault_secret_path,
    )
    database_url = secrets.get("database_url")
    if not database_url:
        raise RuntimeError("database_url not found in environment or Vault")
    return str(database_url)


def _load_settings_with_provider_secrets() -> AppSettings:
    settings = AppSettings()
    try:
        from app.infra.vault_client import init_vault_client, resolve_classifier_secrets

        _apply_optional_provider_settings(
            settings,
            resolve_classifier_secrets(init_vault_client(settings), settings),
        )
    except Exception as exc:
        logger.warning("Could not resolve provider settings from Vault: %s", exc)
    return settings


async def _persist_index(database_url: str, chunks: list[RAGChunk], embeddings) -> None:
    from app.infra.database import create_engine, create_session_factory
    from app.repositories.rag_chunk_repository import RAGChunkRepository
    from app.repositories.rag_embedding_repository import RAGEmbeddingRepository

    engine = create_engine(database_url)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        chunk_repo = RAGChunkRepository(session)
        embedding_repo = RAGEmbeddingRepository(session)
        for chunk in chunks:
            await chunk_repo.insert_chunk(chunk)
            await chunk_repo.insert_sparse_search(
                chunk.chunk_id,
                search_text=f"{chunk.title or ''}\n\n{chunk.content}".strip(),
                title_terms=chunk.title or "",
            )
        for embedding in embeddings:
            await embedding_repo.upsert(embedding)
        await session.commit()
    await engine.dispose()


if __name__ == "__main__":
    import sys

    sys.exit(main())
