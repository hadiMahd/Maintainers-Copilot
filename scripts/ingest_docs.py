"""RAG documentation ingestion command.

Parses project documentation files into normalized RAG source and chunk artifacts.
Outputs:
  - data/processed/rag_doc_sources.jsonl
  - appends to data/processed/rag_chunks.jsonl
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

from app.services.rag_ingestion_service import RAGIngestionService

logger = logging.getLogger(__name__)

_DEFAULT_DOCS_DIR = "docs"
_DEFAULT_OUTPUT_SOURCES = "data/processed/rag_doc_sources.jsonl"
_DEFAULT_OUTPUT_CHUNKS = "data/processed/rag_chunks.jsonl"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest project docs for RAG corpus")
    parser.add_argument("--docs-dir", default=_DEFAULT_DOCS_DIR, help="Path to docs directory")
    parser.add_argument(
        "--output-sources", default=_DEFAULT_OUTPUT_SOURCES, help="Output JSONL for sources"
    )
    parser.add_argument(
        "--output-chunks", default=_DEFAULT_OUTPUT_CHUNKS, help="Output JSONL for chunks"
    )
    parser.add_argument("--max-chunk-tokens", type=int, default=300, help="Max tokens per chunk")
    return parser.parse_args(argv)


def _scan_docs(docs_dir: str) -> list[dict]:
    docs: list[dict] = []
    root = Path(docs_dir)
    if not root.is_dir():
        logger.warning("Docs directory not found: %s", docs_dir)
        return docs
    for md_file in sorted(root.rglob("*.md")):
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            logger.warning("Could not read: %s", md_file)
            continue
        if not content.strip():
            continue
        rel_path = str(md_file.relative_to(root))
        title = md_file.stem.replace("-", " ").replace("_", " ").title()
        docs.append({"source_path": rel_path, "title": title, "content": content})
    logger.info("Scanned %d markdown files from %s", len(docs), docs_dir)
    return docs


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    docs = _scan_docs(args.docs_dir)
    if not docs:
        logger.warning("No documents found in %s", args.docs_dir)
        return 0

    service = RAGIngestionService(max_chunk_tokens=args.max_chunk_tokens)
    sources, chunks = service.ingest_docs(docs)

    os.makedirs(os.path.dirname(args.output_sources), exist_ok=True)
    with open(args.output_sources, "w") as f:
        for s in sources:
            f.write(json.dumps(s.model_dump(), default=str) + "\n")
    logger.info("Wrote %d sources to %s", len(sources), args.output_sources)

    with open(args.output_chunks, "a") as f:
        for c in chunks:
            f.write(json.dumps(c.model_dump(), default=str) + "\n")
    logger.info("Appended %d chunks to %s", len(chunks), args.output_chunks)
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
