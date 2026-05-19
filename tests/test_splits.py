"""Tests for dataset split logic."""

import pytest


def _make_fake_records(count=100):
    """Create fake processed records with deterministic timestamps."""
    records = []
    for i in range(count):
        year = 2020 + (i // 25)
        month = 1 + ((i % 25) // 2)
        day = 1 + (i % 28)
        records.append({
            "id": f"test/repo#{i+1}",
            "issue_number": i + 1,
            "mapped_label": ["bug", "feature", "docs", "question"][i % 4],
            "closed_at": f"{year:04d}-{month:02d}-{day:02d}T00:00:00Z",
        })
    return records


def _split_records(records):
    """Deterministic temporal split logic."""
    sorted_records = sorted(records, key=lambda r: r["closed_at"])
    n = len(sorted_records)

    held_out_end = n
    held_out_start = int(n * 0.95)
    test_end = held_out_start
    test_start = int(n * 0.85)
    val_end = test_start
    val_start = int(n * 0.70)
    train_end = val_start

    splits = {
        "train": sorted_records[:train_end],
        "validation": sorted_records[val_start:val_end],
        "test": sorted_records[test_start:test_end],
        "held_out": sorted_records[held_out_start:held_out_end],
    }
    return splits


@pytest.fixture
def fake_records():
    return _make_fake_records(100)


def test_split_is_deterministic(fake_records):
    """Run split logic twice, assert output is identical."""
    splits1 = _split_records(fake_records)
    splits2 = _split_records(fake_records)
    for key in ["train", "validation", "test", "held_out"]:
        ids1 = [r["id"] for r in splits1[key]]
        ids2 = [r["id"] for r in splits2[key]]
        assert ids1 == ids2


def test_test_split_newer_than_train(fake_records):
    """Assert min(test closed_at) > max(train closed_at)."""
    splits = _split_records(fake_records)
    train_max = max(r["closed_at"] for r in splits["train"])
    test_min = min(r["closed_at"] for r in splits["test"])
    assert test_min > train_max


def test_no_leakage_train_held_out(fake_records):
    """Assert intersection of train and held_out issue_numbers is empty."""
    splits = _split_records(fake_records)
    train_ids = {r["issue_number"] for r in splits["train"]}
    held_out_ids = {r["issue_number"] for r in splits["held_out"]}
    assert train_ids & held_out_ids == set()


def test_no_leakage_train_val_test(fake_records):
    """Assert no issue_number appears in more than one of train/val/test/held_out."""
    splits = _split_records(fake_records)
    all_ids = set()
    for key in ["train", "validation", "test", "held_out"]:
        ids = {r["issue_number"] for r in splits[key]}
        assert all_ids & ids == set(), f"Leakage detected in {key}"
        all_ids |= ids


def test_split_covers_all_records(fake_records):
    """Assert len(train)+len(val)+len(test)+len(held_out) == total."""
    splits = _split_records(fake_records)
    total = sum(len(splits[k]) for k in ["train", "validation", "test", "held_out"])
    assert total == len(fake_records)


def test_approximate_ratios(fake_records):
    """Assert train/total is between 0.60 and 0.80."""
    splits = _split_records(fake_records)
    total = len(fake_records)
    train_ratio = len(splits["train"]) / total
    assert 0.60 <= train_ratio <= 0.80
