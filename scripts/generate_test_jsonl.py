"""Generate test.jsonl from the processed CSV dataset."""

import csv
import json
from pathlib import Path


def generate_test_jsonl(
    csv_path: str = "data/processed/issues_processed_pandas_label_fetch.csv",
    output_path: str = "data/processed/test.jsonl",
) -> None:
    """Extract test split rows and write as JSONL."""
    test_records = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("split") == "test":
                record = {
                    "id": f"pandas-dev/pandas#{row['github_issue_id']}",
                    "repo": row.get("repo", "pandas-dev/pandas"),
                    "issue_number": int(row["github_issue_id"]),
                    "title": row.get("title", ""),
                    "body": row.get("body", ""),
                    "comments": [],
                    "original_labels": eval(row.get("github_labels", "[]")),
                    "mapped_label": row["mapped_label"],
                    "created_at": row.get("created_at", ""),
                    "closed_at": row.get("closed_at", ""),
                    "classifier_text": row.get("clean_text", ""),
                    "rag_text": row.get("clean_text", ""),
                    "source_url": row.get("url", ""),
                }
                test_records.append(record)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        for record in test_records:
            f.write(json.dumps(record) + "\n")

    print(f"Wrote {len(test_records)} test records to {output_path}")


if __name__ == "__main__":
    generate_test_jsonl()
