"""Tests for raw and processed record schemas."""

import pytest


REQUIRED_RAW_FIELDS = [
    "repo",
    "issue_number",
    "title",
    "body",
    "labels",
    "state",
    "created_at",
    "closed_at",
    "updated_at",
    "comments_count",
    "comments_url",
    "comments",
    "html_url",
]

REQUIRED_PROCESSED_FIELDS = [
    "id",
    "repo",
    "issue_number",
    "title",
    "body",
    "comments",
    "original_labels",
    "mapped_label",
    "created_at",
    "closed_at",
    "classifier_text",
    "rag_text",
    "source_url",
]

VALID_LABELS = {"bug", "feature", "docs", "question"}


def test_raw_record_has_required_fields(raw_issue_record):
    """Assert all required fields present and non-None."""
    for field in REQUIRED_RAW_FIELDS:
        assert field in raw_issue_record, f"Missing field: {field}"
        assert raw_issue_record[field] is not None, f"Field is None: {field}"


def test_raw_record_labels_is_list(raw_issue_record):
    """Assert labels field is a list."""
    assert isinstance(raw_issue_record["labels"], list)


def test_processed_record_has_required_fields(processed_issue_record):
    """Assert all required processed fields present."""
    for field in REQUIRED_PROCESSED_FIELDS:
        assert field in processed_issue_record, f"Missing field: {field}"
        assert processed_issue_record[field] is not None, f"Field is None: {field}"


def test_processed_record_mapped_label_is_valid(processed_issue_record):
    """Assert mapped_label is one of valid classes."""
    assert processed_issue_record["mapped_label"] in VALID_LABELS


def test_processed_record_classifier_text_nonempty(processed_issue_record):
    """Assert classifier_text is a non-empty string."""
    text = processed_issue_record["classifier_text"]
    assert isinstance(text, str)
    assert len(text) > 0


def test_raw_record_no_token_field(raw_issue_record):
    """Assert no token-related fields in raw record."""
    forbidden = {"token", "github_token", "authorization"}
    for key in raw_issue_record:
        assert key.lower() not in forbidden, f"Found forbidden field: {key}"
