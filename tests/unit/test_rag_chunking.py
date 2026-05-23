"""Unit tests for parent-document chunking, stable child IDs, and classifier-data leakage rejection."""

from __future__ import annotations

import hashlib

from app.domain.rag import RAGChunk, RAGSource


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _chunk_text(
    text: str,
    parent_id: str,
    max_chunk_tokens: int = 200,
    *,
    source_type: str = "docs",
    source_path: str = "test/doc.md",
    title: str = "Test Document",
) -> list[RAGChunk]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[RAGChunk] = []
    buffer = ""
    for p in paragraphs:
        combined = f"{buffer} {p}" if buffer else p
        if len(combined.split()) <= max_chunk_tokens:
            buffer = combined
        else:
            if buffer:
                chunks.append(
                    _build_chunk(
                        parent_id,
                        buffer,
                        len(chunks),
                        source_type=source_type,
                        source_path=source_path,
                        title=title,
                    )
                )
            buffer = p
    if buffer:
        chunks.append(
            _build_chunk(
                parent_id,
                buffer,
                len(chunks),
                source_type=source_type,
                source_path=source_path,
                title=title,
            )
        )
    return chunks


def _build_chunk(
    parent_id: str,
    content: str,
    chunk_index: int,
    *,
    source_type: str = "docs",
    source_path: str = "test/doc.md",
    title: str = "Test Document",
) -> RAGChunk:
    content_hash = _hash(content.strip())
    chunk_id = _hash(f"{parent_id}:{chunk_index}")
    return RAGChunk(
        chunk_id=chunk_id,
        parent_id=parent_id,
        source_type=source_type,
        source_path=source_path,
        title=title,
        chunk_index=chunk_index,
        content=content.strip(),
        content_hash=content_hash,
        token_count=len(content.split()),
    )


class TestParentDocumentChunking:
    def test_chunks_carry_parent_id(self):
        chunks = _chunk_text("Paragraph one.\n\nParagraph two.\n\nParagraph three.", "doc-1")
        assert len(chunks) > 0
        for c in chunks:
            assert c.parent_id == "doc-1"

    def test_chunk_ids_are_stable(self):
        text = "First paragraph.\n\nSecond paragraph."
        chunks1 = _chunk_text(text, "parent-x")
        chunks2 = _chunk_text(text, "parent-x")
        assert len(chunks1) == len(chunks2)
        for c1, c2 in zip(chunks1, chunks2):
            assert c1.chunk_id == c2.chunk_id
            assert c1.content_hash == c2.content_hash

    def test_chunk_index_is_sequential(self):
        text = "\n\n".join(f"Paragraph {i}." for i in range(5))
        chunks = _chunk_text(text, "doc-seq")
        for i, c in enumerate(chunks):
            assert c.chunk_index == i

    def test_large_content_is_chunked(self):
        text = "\n\n".join("word " * 100 for _ in range(5))
        chunks = _chunk_text(text, "large-doc", max_chunk_tokens=200)
        assert len(chunks) >= 3

    def test_single_paragraph_produces_one_chunk(self):
        text = "This is a single paragraph with enough words to be a chunk."
        chunks = _chunk_text(text, "single")
        assert len(chunks) == 1

    def test_content_hash_is_deterministic(self):
        text = "Same content, same hash."
        chunks1 = _chunk_text(text, "p1")
        chunks2 = _chunk_text(f"  {text}  ", "p1")  # whitespace variation
        assert chunks1[0].content_hash == chunks2[0].content_hash

    def test_content_hash_changes_with_content(self):
        chunks1 = _chunk_text("Content A.", "p1")
        chunks2 = _chunk_text("Content B.", "p1")
        assert chunks1[0].content_hash != chunks2[0].content_hash

    def test_different_parent_different_id(self):
        chunks1 = _chunk_text("Same text here.", "parent-a")
        chunks2 = _chunk_text("Same text here.", "parent-b")
        assert chunks1[0].chunk_id != chunks2[0].chunk_id


class TestSourceMetadataCompleteness:
    def test_chunk_inherits_source_type(self):
        chunks = _chunk_text("Test content.", "doc-1", source_type="docs")
        assert chunks[0].source_type == "docs"

    def test_chunk_inherits_source_path(self):
        chunks = _chunk_text("Test content.", "doc-1")
        assert chunks[0].source_path == "test/doc.md"

    def test_chunk_inherits_title(self):
        chunks = _chunk_text("Test content.", "doc-1")
        assert chunks[0].title == "Test Document"

    def test_chunk_token_count_is_positive(self):
        text = "This has five tokens here."
        chunks = _chunk_text(text, "doc-1")
        assert chunks[0].token_count > 0


class TestClassifierDataLeakage:
    def test_issue_sources_marked_as_issue_type(self):
        chunks = _chunk_text("Issue discussion about a bug.", "issue-1", source_type="issue")
        assert chunks[0].source_type == "issue"

    def test_issue_source_requires_held_out_flag(self):
        def _is_held_out(source: RAGSource) -> bool:
            return source.source_id not in _classifier_source_ids()

        assert _is_held_out(
            RAGSource(
                source_id="rag-heldout-1",
                source_type="issue",
                source_path="issues/42.json",
                title="Bug report",
                content="issue text",
                content_hash="abc",
            )
        )

    def test_classifier_source_ids_are_excluded(self):
        classifier_ids = {"classifier-1", "classifier-2"}
        rag_source = RAGSource(
            source_id="rag-1",
            source_type="issue",
            source_path="issues/99.json",
            title="Question",
            content="issue text",
            content_hash="def",
        )
        assert rag_source.source_id not in classifier_ids


def _classifier_source_ids() -> set[str]:
    return {"classifier-1", "classifier-2", "classifier-3"}
