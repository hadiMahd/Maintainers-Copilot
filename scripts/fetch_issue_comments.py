#!/usr/bin/env python3
"""Enrich raw issue records with comments."""

import asyncio
import json
import os
import sys
import tempfile

from config.dataset_settings import DatasetSettings
from app.infra.github_client import GitHubClient


async def main() -> None:
    """Read raw issues, enrich with comments, write back atomically."""
    settings = DatasetSettings()
    token = (
        settings.github_token.get_secret_value()
        if settings.github_token
        else None
    )
    client = GitHubClient(token=token)

    if not os.path.exists(settings.raw_issues_path):
        print(f"Error: {settings.raw_issues_path} not found", file=sys.stderr)
        sys.exit(1)

    records = []
    with open(settings.raw_issues_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    enriched = 0
    for record in records:
        comments_count = record.get("comments_count", 0)
        comments_url = record.get("comments_url")
        if comments_count > 0 and comments_url:
            try:
                comments = await client.get_issue_comments(comments_url)
                record["comments"] = [
                    {
                        "body": c.get("body") or "",
                        "author_association": c.get("author_association"),
                        "created_at": c.get("created_at"),
                    }
                    for c in comments
                ]
                enriched += 1
            except RuntimeError as exc:
                print(f"Error: {exc}", file=sys.stderr)
                sys.exit(1)
                # Log but don't fail on other errors
                record["comments"] = []
        else:
            record["comments"] = []

    # Atomic write
    fd, tmp_path = tempfile.mkstemp(
        dir=os.path.dirname(settings.raw_issues_path) or "."
    )
    try:
        with os.fdopen(fd, "w") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")
        os.replace(tmp_path, settings.raw_issues_path)
    except Exception:
        os.remove(tmp_path)
        raise

    print(
        f"Enriched {enriched} records with comments; "
        f"wrote {len(records)} records to {settings.raw_issues_path}"
    )


if __name__ == "__main__":
    asyncio.run(main())
