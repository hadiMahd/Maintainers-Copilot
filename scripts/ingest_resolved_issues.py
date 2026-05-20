"""RAG resolved-issue ingestion command.

Ingests held-out resolved issues with maintainer answers into the RAG corpus.
Prevents overlap with classifier training data.

Outputs:
  - data/processed/rag_issue_answer_sources.jsonl
  - appends to data/processed/rag_chunks.jsonl
"""

from __future__ import annotations

import argparse
import json
import logging
import os

from app.services.rag_ingestion_service import RAGIngestionService

logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_SOURCES = "data/processed/rag_issue_answer_sources.jsonl"
_DEFAULT_OUTPUT_CHUNKS = "data/processed/rag_chunks.jsonl"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest resolved issues for RAG corpus")
    parser.add_argument("--input", required=True, help="Path to issues JSONL input file")
    parser.add_argument("--output-sources", default=_DEFAULT_OUTPUT_SOURCES, help="Output JSONL for sources")
    parser.add_argument("--output-chunks", default=_DEFAULT_OUTPUT_CHUNKS, help="Output JSONL for chunks")
    parser.add_argument("--max-chunk-tokens", type=int, default=300, help="Max tokens per chunk")
    parser.add_argument("--classifier-source-ids", help="Path to file with classifier source IDs (one per line)")
    return parser.parse_args(argv)


def _load_issues(path: str) -> list[dict]:
    issues: list[dict] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            issues.append(json.loads(line))
    logger.info("Loaded %d issues from %s", len(issues), path)
    return issues


def _load_classifier_ids(path: str | None) -> set[str]:
    if not path or not os.path.isfile(path):
        return set()
    ids: set[str] = set()
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                ids.add(line)
    logger.info("Loaded %d classifier source IDs from %s", len(ids), path)
    return ids


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    issues = _load_issues(args.input)
    if not issues:
        logger.warning("No issues found in %s", args.input)
        return 0

    classifier_ids = _load_classifier_ids(args.classifier_source_ids)
    service = RAGIngestionService(
        max_chunk_tokens=args.max_chunk_tokens,
        classifier_source_ids=classifier_ids,
    )
    sources, chunks = service.ingest_resolved_issues(issues)

    os.makedirs(os.path.dirname(args.output_sources), exist_ok=True)
    with open(args.output_sources, "w") as f:
        for s in sources:
            f.write(json.dumps(s.model_dump(), default=str) + "\n")
    logger.info("Wrote %d issue sources to %s", len(sources), args.output_sources)

    with open(args.output_chunks, "a") as f:
        for c in chunks:
            f.write(json.dumps(c.model_dump(), default=str) + "\n")
    logger.info("Appended %d issue chunks to %s", len(chunks), args.output_chunks)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
