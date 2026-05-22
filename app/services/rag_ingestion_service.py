"""RAG ingestion service — normalized doc and issue source parsing, parent-document chunking."""

from __future__ import annotations

import hashlib
import logging

from app.domain.rag import (
    RAGChunk,
    RAGSource,
    ResolvedIssueAnswer,
)

logger = logging.getLogger(__name__)

DEFAULT_MAX_CHUNK_TOKENS = 300


def _stable_hash(*parts: str) -> str:
    return hashlib.sha256(":".join(parts).encode()).hexdigest()


def _chunk_text(
    text: str,
    parent_id: str,
    *,
    source_type: str,
    source_path: str | None = None,
    title: str | None = None,
    source_url: str | None = None,
    issue_number: int | None = None,
    labels: list[str] | None = None,
    max_chunk_tokens: int = DEFAULT_MAX_CHUNK_TOKENS,
) -> list[RAGChunk]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []
    chunks: list[RAGChunk] = []
    buffer = ""
    for p in paragraphs:
        combined = f"{buffer}\n\n{p}" if buffer else p
        if len(combined.split()) <= max_chunk_tokens:
            buffer = combined
        else:
            if buffer:
                chunks.append(
                    _make_chunk(
                        parent_id=parent_id,
                        content=buffer.strip(),
                        chunk_index=len(chunks),
                        source_type=source_type,
                        source_path=source_path,
                        title=title,
                        source_url=source_url,
                        issue_number=issue_number,
                        labels=labels,
                    )
                )
            buffer = p
    if buffer:
        chunks.append(
            _make_chunk(
                parent_id=parent_id,
                content=buffer.strip(),
                chunk_index=len(chunks),
                source_type=source_type,
                source_path=source_path,
                title=title,
                source_url=source_url,
                issue_number=issue_number,
                labels=labels,
            )
        )
    return chunks


def _make_chunk(
    *,
    parent_id: str,
    content: str,
    chunk_index: int,
    source_type: str,
    source_path: str | None = None,
    title: str | None = None,
    source_url: str | None = None,
    issue_number: int | None = None,
    labels: list[str] | None = None,
) -> RAGChunk:
    content_stripped = content.strip()
    return RAGChunk(
        chunk_id=_stable_hash(parent_id, str(chunk_index)),
        parent_id=parent_id,
        source_type=source_type,
        source_path=source_path,
        issue_number=issue_number,
        source_url=source_url,
        title=title,
        labels=list(labels) if labels else [],
        chunk_index=chunk_index,
        content=content_stripped,
        content_hash=_stable_hash(content_stripped),
        token_count=len(content_stripped.split()),
    )


class RAGIngestionService:
    """Parse docs and held-out issue sources into RAGSource + RAGChunk records."""

    def __init__(
        self,
        *,
        max_chunk_tokens: int = DEFAULT_MAX_CHUNK_TOKENS,
        classifier_source_ids: set[str] | None = None,
    ) -> None:
        self._max_chunk_tokens = max_chunk_tokens
        self._classifier_source_ids = classifier_source_ids or set()

    def ingest_docs(
        self,
        docs: list[dict],
    ) -> tuple[list[RAGSource], list[RAGChunk]]:
        sources: list[RAGSource] = []
        chunks: list[RAGChunk] = []
        for doc in docs:
            source_path = doc["source_path"]
            title = doc.get("title", source_path)
            content = doc.get("content", "")
            source_id = _stable_hash(source_path)
            content_hash = _stable_hash(content)
            sources.append(
                RAGSource(
                    source_id=source_id,
                    source_type="docs",
                    source_path=source_path,
                    source_url=doc.get("source_url"),
                    title=title,
                    content=content,
                    content_hash=content_hash,
                )
            )
            child_chunks = _chunk_text(
                content,
                parent_id=source_id,
                source_type="docs",
                source_path=source_path,
                title=title,
                source_url=doc.get("source_url"),
                max_chunk_tokens=self._max_chunk_tokens,
            )
            chunks.extend(child_chunks)
        logger.info("Ingested %d docs → %d chunks", len(sources), len(chunks))
        return sources, chunks

    def ingest_resolved_issues(
        self,
        issues: list[dict],
    ) -> tuple[list[ResolvedIssueAnswer], list[RAGChunk]]:
        sources: list[ResolvedIssueAnswer] = []
        chunks: list[RAGChunk] = []
        for issue in issues:
            issue_number = issue.get("issue_number")
            source_id = _stable_hash(f"issue:{issue_number}")
            if source_id in self._classifier_source_ids:
                logger.warning(
                    "Skipping issue %d — overlaps with classifier training data",
                    issue_number,
                )
                continue
            title = issue.get("title", f"Issue #{issue_number}")
            question_context = issue.get("question_context", "")
            maintainer_answer = issue.get("maintainer_answer", "")
            content = f"{title}\n\n{question_context}\n\n{maintainer_answer}"
            content_hash = _stable_hash(content)
            sources.append(
                ResolvedIssueAnswer(
                    source_id=source_id,
                    source_path=f"issues/{issue_number}.json",
                    source_url=issue.get("source_url"),
                    title=title,
                    content=content,
                    content_hash=content_hash,
                    issue_number=issue_number,
                    labels=issue.get("labels", []),
                    created_at=issue.get("created_at"),
                    updated_at=issue.get("updated_at"),
                    question_context=question_context,
                    maintainer_answer=maintainer_answer,
                )
            )
            child_chunks = _chunk_text(
                content,
                parent_id=source_id,
                source_type="issue",
                source_path=f"issues/{issue_number}.json",
                title=title,
                source_url=issue.get("source_url"),
                issue_number=issue_number,
                labels=issue.get("labels", []),
                max_chunk_tokens=self._max_chunk_tokens,
            )
            chunks.extend(child_chunks)
        logger.info("Ingested %d issues → %d chunks", len(sources), len(chunks))
        return sources, chunks


__all__ = ["RAGIngestionService", "_chunk_text", "_stable_hash", "DEFAULT_MAX_CHUNK_TOKENS"]
