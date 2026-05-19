"""Tests for label mapping logic."""

import pytest


def _map_label(labels, mapping):
    """Apply label mapping logic."""
    if not labels:
        return None

    classes = mapping["classes"]
    ambiguous_policy = mapping["ambiguous_policy"]
    priority_order = mapping.get("priority_order", [])
    unmapped_policy = mapping.get("unmapped_policy", "exclude")

    # Collect all matching classes for the given labels
    matches = []
    for label in labels:
        for cls, source_labels in classes.items():
            if label in source_labels:
                matches.append(cls)
                break

    if not matches:
        return None if unmapped_policy == "exclude" else "unknown"

    if len(matches) == 1:
        return matches[0]

    # Ambiguous: multiple classes matched
    if ambiguous_policy == "first_match":
        for cls in priority_order:
            if cls in matches:
                return cls
        return matches[0]

    return None if unmapped_policy == "exclude" else "ambiguous"


def test_valid_label_maps_correctly(sample_label_mapping):
    """Given a raw record with labels=['bug'], assert mapped_label is 'bug'."""
    assert _map_label(["bug"], sample_label_mapping) == "bug"


def test_unmapped_label_excluded(sample_label_mapping):
    """Given labels=['invalid_label'] and unmapped_policy=exclude, assert excluded."""
    assert _map_label(["invalid_label"], sample_label_mapping) is None


def test_ambiguous_label_uses_first_match(sample_label_mapping):
    """Given labels=['bug','feature'] and ambiguous_policy=first_match, assert priority_order followed."""
    result = _map_label(["bug", "feature"], sample_label_mapping)
    assert result == "bug"  # bug comes first in priority_order


def test_empty_labels_excluded(sample_label_mapping):
    """Given labels=[], assert record is excluded."""
    assert _map_label([], sample_label_mapping) is None


def test_mapped_label_is_valid_class(sample_label_mapping):
    """Assert mapped_label is always one of valid classes or excluded."""
    valid = {"bug", "feature", "docs", "question"}
    test_cases = [
        (["bug"], "bug"),
        (["feature"], "feature"),
        (["documentation"], "docs"),
        (["question"], "question"),
        (["invalid"], None),
    ]
    for labels, expected in test_cases:
        result = _map_label(labels, sample_label_mapping)
        assert result == expected, f"Failed for labels={labels}"
        if result is not None:
            assert result in valid
