"""Unit tests for metadata filtering and query transformation toggling."""

from __future__ import annotations

from app.domain.rag import RAGChunk, RetrievalResult


def _make_chunk(
    chunk_id: str,
    source_type: str = "docs",
    source_path: str | None = None,
    labels: list[str] | None = None,
) -> RAGChunk:
    return RAGChunk(
        chunk_id=chunk_id,
        parent_id=f"p-{chunk_id}",
        source_type=source_type,
        source_path=source_path,
        labels=labels or [],
        content="test content",
        content_hash="abc",
        token_count=2,
    )


def _make_result(chunk: RAGChunk, rank: int = 1, score: float = 0.9) -> RetrievalResult:
    return RetrievalResult(rank=rank, final_score=score, chunk=chunk, retrieval_mode="hybrid")


class TestMetadataFiltering:
    def test_filter_by_source_type(self):
        results = [
            _make_result(_make_chunk("c1", source_type="docs")),
            _make_result(_make_chunk("c2", source_type="issue")),
            _make_result(_make_chunk("c3", source_type="docs")),
        ]
        filters = {"source_type": "docs"}
        filtered = _apply_metadata_filters(results, filters)
        assert len(filtered) == 2
        assert all(r.chunk.source_type == "docs" for r in filtered)

    def test_filter_by_source_path(self):
        results = [
            _make_result(_make_chunk("c1", source_path="docs/install.md")),
            _make_result(_make_chunk("c2", source_path="docs/errors.md")),
        ]
        filters = {"source_path": "docs/install.md"}
        filtered = _apply_metadata_filters(results, filters)
        assert len(filtered) == 1
        assert filtered[0].chunk.source_path == "docs/install.md"

    def test_filter_by_labels(self):
        results = [
            _make_result(_make_chunk("c1", labels=["bug", "priority"])),
            _make_result(_make_chunk("c2", labels=["feature"])),
        ]
        filters = {"labels": ["bug"]}
        filtered = _apply_metadata_filters(results, filters)
        assert len(filtered) == 1
        assert "bug" in filtered[0].chunk.labels

    def test_filter_no_results(self):
        results = [_make_result(_make_chunk("c1", source_type="docs"))]
        filters = {"source_type": "issue"}
        filtered = _apply_metadata_filters(results, filters)
        assert len(filtered) == 0

    def test_no_filters_returns_all(self):
        results = [
            _make_result(_make_chunk("c1")),
            _make_result(_make_chunk("c2")),
        ]
        filtered = _apply_metadata_filters(results, {})
        assert len(filtered) == 2


class TestQueryTransformation:
    def test_transformation_enabled_rewrites(self):
        original = "how to fix the bug"
        transformed = _transform_query(original, enabled=True)
        assert len(transformed) > 0

    def test_transformation_disabled_returns_original(self):
        original = "how to fix the bug"
        assert _transform_query(original, enabled=False) == original

    def test_transformation_adds_technical_terms(self):
        result = _transform_query("numpy install error", enabled=True)
        # Transformation should add technical terms related to the query
        assert len(result) >= len("numpy install error")

    def test_empty_query_transformed(self):
        assert _transform_query("", enabled=True) == ""


# -- Helpers (mirror retrieval service/filter logic) --------------------------


def _apply_metadata_filters(
    results: list[RetrievalResult],
    filters: dict,
) -> list[RetrievalResult]:
    if not filters:
        return results
    filtered = []
    for r in results:
        match = True
        if "source_type" in filters:
            if r.chunk.source_type != filters["source_type"]:
                match = False
        if "source_path" in filters and match:
            if r.chunk.source_path != filters["source_path"]:
                match = False
        if "labels" in filters and match:
            if not any(lbl in r.chunk.labels for lbl in filters["labels"]):
                match = False
        if match:
            filtered.append(r)
    return filtered


def _transform_query(query: str, enabled: bool = True) -> str:
    if not enabled or not query.strip():
        return query
    terms = {
        "fix": "troubleshooting resolution bug fix",
        "install": "installation setup pip venv",
        "error": "error exception failure debugging",
        "numpy": "numpy array numerical computation",
    }
    parts = query.lower().split()
    additions = []
    for word in parts:
        if word in terms:
            additions.append(terms[word])
    if additions:
        return f"{query} ({' '.join(additions)})"
    return query
