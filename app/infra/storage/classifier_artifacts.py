"""MinIO classifier artifact and manifest helpers.

Handles uploading hash-validated artifacts and manifests to MinIO,
and atomic writes of manifest JSON.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import tempfile
from datetime import UTC
from pathlib import Path

from app.domain.classifier import ArtifactManifest
from app.domain.errors import ConfigError

ARTIFACT_HASH_EXCLUDED_FILES = frozenset(
    {
        "artifact.sha256",
        "manifest.json",
        "model_card.json",
        "run_metadata.json",
    }
)


def iter_hashable_files(artifact_dir: Path) -> list[Path]:
    """Return the artifact files that contribute to deployable hashing."""
    return [
        file_path
        for file_path in sorted(artifact_dir.rglob("*"))
        if file_path.is_file() and file_path.name not in ARTIFACT_HASH_EXCLUDED_FILES
    ]


def compute_artifact_sha256(artifact_dir: Path) -> str:
    """Compute SHA-256 over all files in an artifact directory.

    Files are sorted by name for deterministic hashing. Metadata files that
    embed the hash themselves are excluded so deployable artifacts can be
    verified after model-card and manifest generation.
    """
    sha256 = hashlib.sha256()
    for file_path in iter_hashable_files(artifact_dir):
        relative = file_path.relative_to(artifact_dir)
        sha256.update(str(relative).encode())
        sha256.update(file_path.read_bytes())
    return sha256.hexdigest()


def compute_training_data_hash(data_path: str) -> str:
    """Compute SHA-256 of a training data file."""
    path = Path(data_path)
    if not path.exists():
        raise ConfigError(f"Training data file not found: {data_path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest(
    model_version: str,
    approach: str,
    artifact_sha256: str,
    training_data_hash: str,
    source_artifact_path: str,
    minio_object_key: str,
) -> ArtifactManifest:
    """Build an ArtifactManifest with the given fields."""
    return ArtifactManifest(
        model_version=model_version,
        approach=approach,
        artifact_sha256=artifact_sha256,
        training_data_hash=training_data_hash,
        source_artifact_path=source_artifact_path,
        minio_object_key=minio_object_key,
        uploaded_at=_now_iso(),
    )


def save_manifest(manifest: ArtifactManifest, path: str) -> None:
    """Atomically write manifest JSON to disk."""
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".json", dir=os.path.dirname(path) or ".")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            f.write(manifest.model_dump_json(indent=2))
        os.replace(tmp_path, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise


def validate_artifact_hash(artifact_dir: Path, expected_sha256: str) -> bool:
    """Verify the computed artifact hash matches the expected value."""
    return compute_artifact_sha256(artifact_dir) == expected_sha256


def write_artifact_sha256(artifact_dir: Path, sha256_value: str) -> Path:
    """Persist the deployable artifact hash alongside the artifact."""
    hash_path = artifact_dir / "artifact.sha256"
    hash_path.write_text(f"{sha256_value}\n")
    return hash_path


def _now_iso() -> str:
    """Return current UTC time as ISO-8601 string."""
    from datetime import datetime

    return datetime.now(UTC).isoformat()
