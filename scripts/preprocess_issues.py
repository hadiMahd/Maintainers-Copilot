#!/usr/bin/env python3
"""Preprocess raw issues: normalize and map labels into project classes."""

import json
import os
import sys
import tempfile

import yaml

from config.dataset_settings import DatasetSettings


def _map_label(labels, mapping):
    """Apply label mapping logic."""
    if not labels:
        return None

    classes = mapping["classes"]
    ambiguous_policy = mapping["ambiguous_policy"]
    priority_order = mapping.get("priority_order", [])
    unmapped_policy = mapping.get("unmapped_policy", "exclude")

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

    if ambiguous_policy == "first_match":
        for cls in priority_order:
            if cls in matches:
                return cls
        return matches[0]

    return None if unmapped_policy == "exclude" else "ambiguous"


def main() -> None:
    """Read raw issues, apply label mapping, write processed records."""
    settings = DatasetSettings()

    if not os.path.exists(settings.raw_issues_path):
        print(f"Error: {settings.raw_issues_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(settings.label_mapping_path, "r") as f:
        label_mapping = yaml.safe_load(f)

    processed = []
    excluded = {"unmapped": 0, "empty": 0, "ambiguous": 0}

    with open(settings.raw_issues_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)

            mapped = _map_label(raw.get("labels", []), label_mapping)
            if mapped is None:
                if not raw.get("labels"):
                    excluded["empty"] += 1
                else:
                    excluded["unmapped"] += 1
                continue

            comments = raw.get("comments", [])
            comments_text = "\n\n".join(c.get("body", "") for c in comments if c.get("body"))

            body = raw.get("body") or ""
            title = raw.get("title") or ""
            classifier_text = f"{title}\n\n{body}".strip()
            rag_text = f"{title}\n\n{body}"
            if comments_text:
                rag_text += f"\n\n{comments_text}"
            rag_text = rag_text.strip()

            record = {
                "id": f"{raw['repo']}#{raw['issue_number']}",
                "repo": raw["repo"],
                "issue_number": raw["issue_number"],
                "title": title,
                "body": body,
                "comments": [c.get("body", "") for c in comments],
                "original_labels": raw.get("labels", []),
                "mapped_label": mapped,
                "created_at": raw.get("created_at"),
                "closed_at": raw.get("closed_at"),
                "classifier_text": classifier_text,
                "rag_text": rag_text,
                "source_url": raw.get("html_url", ""),
            }
            processed.append(record)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(settings.processed_issues_path), exist_ok=True)

    # Atomic write
    fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(settings.processed_issues_path) or ".")
    try:
        with os.fdopen(fd, "w") as f:
            for record in processed:
                f.write(json.dumps(record) + "\n")
        os.replace(tmp_path, settings.processed_issues_path)
    except Exception:
        os.remove(tmp_path)
        raise

    total_excluded = sum(excluded.values())
    print(
        f"Processed {len(processed)} records; "
        f"excluded {total_excluded} "
        f"(empty_labels={excluded['empty']}, "
        f"unmapped={excluded['unmapped']}, "
        f"ambiguous={excluded['ambiguous']})"
    )


if __name__ == "__main__":
    main()
