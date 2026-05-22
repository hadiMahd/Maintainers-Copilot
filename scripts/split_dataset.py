#!/usr/bin/env python3
"""Create deterministic temporal dataset splits."""

import json
import os
import sys
import tempfile

from config.dataset_settings import DatasetSettings


def main() -> None:
    """Read processed issues, split temporally, write split files."""
    settings = DatasetSettings()

    if not os.path.exists(settings.processed_issues_path):
        print(
            f"Error: {settings.processed_issues_path} not found",
            file=sys.stderr,
        )
        sys.exit(1)

    records = []
    with open(settings.processed_issues_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    # Sort by closed_at ascending for determinism
    records.sort(key=lambda r: r.get("closed_at", ""))
    n = len(records)

    # Temporal split: last 5% held_out, next 10% test, next 15% val, rest train
    held_out_start = int(n * 0.95)
    test_start = int(n * 0.85)
    val_start = int(n * 0.70)

    splits = {
        "train": records[:val_start],
        "validation": records[val_start:test_start],
        "test": records[test_start:held_out_start],
        "held_out": records[held_out_start:],
    }

    # Ensure splits directory exists
    os.makedirs(settings.splits_dir, exist_ok=True)

    # Write each split atomically
    for name, split_records in splits.items():
        path = os.path.join(settings.splits_dir, f"{name}.jsonl")
        fd, tmp_path = tempfile.mkstemp(dir=settings.splits_dir)
        try:
            with os.fdopen(fd, "w") as f:
                for r in split_records:
                    f.write(json.dumps(r) + "\n")
            os.replace(tmp_path, path)
        except Exception:
            os.remove(tmp_path)
            raise
        print(f"  {name}: {len(split_records)} records → {path}")

    # Compute per-split class distribution
    class_counts = {}
    limitations = []
    for name, split_records in splits.items():
        counts = {}
        for r in split_records:
            label = r.get("mapped_label", "unknown")
            counts[label] = counts.get(label, 0) + 1
        class_counts[name] = counts
        # Check for missing classes in train
        if name == "train":
            all_classes = {"bug", "feature", "docs", "question"}
            present = set(counts.keys())
            missing = all_classes - present
            if missing:
                limitations.append(f"Train split missing classes: {sorted(missing)}")
                print(f"WARNING: Train split missing classes: {sorted(missing)}")

    # Write limitations sidecar
    limitations_path = os.path.join(settings.splits_dir, "split_limitations.json")
    with open(limitations_path, "w") as f:
        json.dump({"limitations": limitations}, f, indent=2)

    print(f"Splits written to {settings.splits_dir}")


if __name__ == "__main__":
    main()
