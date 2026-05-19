#!/usr/bin/env python3
"""Fetch closed GitHub issues for the configured repository."""

import asyncio
import json
import os
import sys
import tempfile

from config.dataset_settings import DatasetSettings
from app.infra.github_client import GitHubClient


async def main() -> None:
    """Fetch issues and write to raw JSONL file."""
    settings = DatasetSettings()
    token = (
        settings.github_token.get_secret_value()
        if settings.github_token
        else None
    )
    client = GitHubClient(token=token)

    try:
        issues = await client.get_closed_issues(
            settings.repo_owner,
            settings.repo_name,
            settings.max_issues,
        )
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(settings.raw_issues_path), exist_ok=True)

    # Map API responses to raw issue records
    records = []
    for item in issues:
        # Skip pull requests (GitHub API returns PRs in issues endpoint)
        if item.get("pull_request"):
            continue

        record = {
            "repo": f"{settings.repo_owner}/{settings.repo_name}",
            "issue_number": item.get("number"),
            "title": item.get("title", ""),
            "body": item.get("body") or "",
            "labels": [label["name"] for label in item.get("labels", [])],
            "state": item.get("state"),
            "created_at": item.get("created_at"),
            "closed_at": item.get("closed_at"),
            "updated_at": item.get("updated_at"),
            "author_association": item.get("author_association"),
            "comments_count": item.get("comments", 0),
            "comments_url": item.get("comments_url"),
            "comments": [],
            "html_url": item.get("html_url"),
        }
        records.append(record)

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

    print(f"Fetched {len(records)} issues to {settings.raw_issues_path}")


if __name__ == "__main__":
    asyncio.run(main())
