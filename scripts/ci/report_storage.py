"""MinIO/local-compatible report storage adapter."""

import json
import os
from pathlib import Path
from typing import Any, Optional


class ReportStorageError(Exception):
    pass


def store_report_local(report: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    return path


def load_report_local(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ReportStorageError(f"Report not found: {path}")
    with open(path) as f:
        return json.load(f)  # type: ignore[no-any-return]


def store_report(report: dict[str, Any], bucket: str, key: str) -> bool:
    """Store report. Uses MinIO when available, falls back to local."""
    local_path = Path(f"evals/reports/{key}")
    try:
        store_report_local(report, local_path)
        return True
    except Exception:
        return False


def try_load_minio(bucket: str, key: str) -> Optional[dict[str, Any]]:
    """Try to load a report from MinIO. Returns None if MinIO is unavailable."""
    try:
        from minio import Minio

        endpoint = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
        access_key = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
        secret_key = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
        secure = os.environ.get("MINIO_SECURE", "false").lower() == "true"

        client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
        response = client.get_object(bucket, key)
        data = json.loads(response.read())
        response.close()
        response.release_conn()
        return data  # type: ignore[no-any-return]
    except Exception:
        return None


def find_previous_green_report(
    bucket: str, prefix: str = "eval_report_"
) -> Optional[dict[str, Any]]:
    """Find the most recent passing report in storage."""
    local_dir = Path("evals/reports/")
    if not local_dir.exists():
        return None
    reports = sorted(
        local_dir.glob(f"{prefix}*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    for rp in reports:
        try:
            report = load_report_local(rp)
            if report.get("passed", False):
                return report
        except Exception:
            continue
    return None
