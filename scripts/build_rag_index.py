"""RAG index building command.

Builds or updates sparse and dense retrieval indexes for the RAG corpus.
Generates embeddings using local all-MiniLM-L6-v2 (default) or optional
Azure text-embedding-3-small when configured.

Outputs:
  - artifacts/rag/embedding_comparison.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

from app.core.config import AppSettings
from app.infra.embedding_client import (
    LocalEmbeddingClient,
    FakeEmbeddingClient,
    resolve_embedding_client,
)
from app.services.rag_index_service import RAGIndexService
from app.domain.rag import RAGChunk

logger = logging.getLogger(__name__)

_DEFAULT_CHUNKS_PATH = "data/processed/rag_chunks.jsonl"
_DEFAULT_COMPARISON_OUTPUT = "artifacts/rag/embedding_comparison.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build RAG index from chunk corpus")
    parser.add_argument("--chunks", default=_DEFAULT_CHUNKS_PATH, help="Path to chunks JSONL")
    parser.add_argument("--output", default=_DEFAULT_COMPARISON_OUTPUT, help="Path to comparison output JSON")
    parser.add_argument("--fake", action="store_true", help="Use fake embedding client (for testing)")
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
        settings = AppSettings(_env_file=None)
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
    logger.info(
        "Embedding comparison saved to %s: local=%d/%d",
        args.output,
        len(deduped),
        len(chunks),
    )
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
