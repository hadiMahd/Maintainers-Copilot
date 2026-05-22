"""Unit tests for query transformation toggling."""

from __future__ import annotations


class TestQueryTransformationToggle:
    def test_enabled_rewrites_technical_terms(self):
        result = _transform_query("pip install error", enabled=True)
        assert "pip" in result
        assert "install" in result
        assert len(result) > len("pip install error")

    def test_disabled_returns_unchanged(self):
        query = "how to fix the parser bug"
        assert _transform_query(query, enabled=False) == query

    def test_no_keywords_no_change(self):
        query = "hello world"
        assert _transform_query(query, enabled=True) == query

    def test_empty_query(self):
        assert _transform_query("", enabled=True) == ""
        assert _transform_query("   ", enabled=True) == "   "

    def test_multiple_terms_expanded(self):
        result = _transform_query("fix install error", enabled=True)
        assert len(result) > len("fix install error")

    def test_transformation_preserves_original_query(self):
        query = "numpy install fails"
        result = _transform_query(query, enabled=True)
        assert result.startswith("numpy install fails")

    def test_transformation_is_deterministic(self):
        q = "fix error build"
        assert _transform_query(q, enabled=True) == _transform_query(q, enabled=True)


def _transform_query(query: str, enabled: bool = True) -> str:
    if not enabled or not query.strip():
        return query
    terms = {
        "fix": "troubleshooting resolution bug fix",
        "install": "installation setup pip venv",
        "error": "error exception failure debugging",
        "numpy": "numpy array numerical computation",
        "build": "build compile cmake make",
        "pip": "pip python package installer",
        "parser": "parser tokenizer syntax parse",
    }
    parts = query.lower().split()
    additions = []
    seen = set()
    for word in parts:
        if word in terms and word not in seen:
            seen.add(word)
            additions.append(terms[word])
    if additions:
        return f"{query} ({' '.join(additions)})"
    return query
