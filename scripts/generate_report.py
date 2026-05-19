#!/usr/bin/env python3
"""Generate dataset statistics report."""

import json
import os
import sys
import tempfile
from datetime import datetime

from config.dataset_settings import DatasetSettings


def _load_jsonl(path):
    """Load records from a JSONL file."""
    if not os.path.exists(path):
        return []
    records = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def main() -> None:
    """Read split files and generate dataset report."""
    settings = DatasetSettings()

    raw_records = _load_jsonl(settings.raw_issues_path)
    processed_records = _load_jsonl(settings.processed_issues_path)

    splits = {}
    for name in ["train", "validation", "test", "held_out"]:
        path = os.path.join(settings.splits_dir, f"{name}.jsonl")
        splits[name] = _load_jsonl(path)

    # Count class distributions per split
    split_stats = {}
    for name, records in splits.items():
        class_counts = {}
        dates = []
        for r in records:
            label = r.get("mapped_label", "unknown")
            class_counts[label] = class_counts.get(label, 0) + 1
            closed_at = r.get("closed_at")
            if closed_at:
                dates.append(closed_at)
        split_stats[name] = {
            "count": len(records),
            "class_counts": class_counts,
            "min_date": min(dates) if dates else None,
            "max_date": max(dates) if dates else None,
        }

    # Load limitations
    limitations = []
    limitations_path = os.path.join(
        settings.splits_dir, "split_limitations.json"
    )
    if os.path.exists(limitations_path):
        with open(limitations_path, "r") as f:
            data = json.load(f)
            limitations.extend(data.get("limitations", []))

    # Collect unmapped labels (labels in raw that don't appear in processed)
    raw_labels = set()
    for r in raw_records:
        for label in r.get("labels", []):
            raw_labels.add(label)

    processed_labels = set()
    for r in processed_records:
        for label in r.get("original_labels", []):
            processed_labels.add(label)

    unmapped_labels = sorted(raw_labels - processed_labels)

    report = {
        "source_repository": f"{settings.repo_owner}/{settings.repo_name}",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_raw": len(raw_records),
        "total_processed": len(processed_records),
        "total_excluded": len(raw_records) - len(processed_records),
        "splits": split_stats,
        "unmapped_labels": unmapped_labels,
        "limitations": limitations,
    }

    # Ensure output directory exists
    report_dir = os.path.dirname(settings.report_path) or "."
    os.makedirs(report_dir, exist_ok=True)

    # Atomic write
    fd, tmp_path = tempfile.mkstemp(dir=report_dir)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(report, f, indent=2)
        os.replace(tmp_path, settings.report_path)
    except Exception:
        os.remove(tmp_path)
        raise

    print(f"Report written to {settings.report_path}")
    print(f"  Raw: {report['total_raw']}")
    print(f"  Processed: {report['total_processed']}")
    print(f"  Excluded: {report['total_excluded']}")


if __name__ == "__main__":
    main()
