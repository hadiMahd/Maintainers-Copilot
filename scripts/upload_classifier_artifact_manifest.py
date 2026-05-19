"""Upload or manifest the selected classifier artifact to MinIO.

Only hash-validated deployable artifacts are uploaded. No secrets,
provider credentials, or incomplete run state are ever uploaded.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.infra.storage.classifier_artifacts import (
    build_manifest,
    save_manifest,
    validate_artifact_hash,
)


def upload_classifier_artifact_manifest(
    artifact_dir: str = "artifacts/classifiers/transformer",
    model_card_path: str | None = None,
    minio_bucket: str = "maintainer-classifiers",
) -> None:
    """Validate and upload or manifest the selected classifier artifact.

    Reads the model card, validates the artifact hash, and writes a manifest.
    If MinIO is available, attempts upload. Otherwise, writes a local manifest.
    """
    artifact_path = Path(artifact_dir)
    if not artifact_path.exists():
        print(f"Error: Artifact directory not found: {artifact_dir}")
        sys.exit(1)

    # Load model card
    if model_card_path is None:
        model_card_path = str(artifact_path / "model_card.json")
    card_path = Path(model_card_path)
    if not card_path.exists():
        print(f"Error: Model card not found: {model_card_path}")
        sys.exit(1)

    model_card = json.loads(card_path.read_text())

    # Validate artifact hash
    expected_hash = model_card.get("artifact_sha256")
    if not expected_hash:
        print("Error: Model card missing artifact_sha256")
        sys.exit(1)

    if not validate_artifact_hash(artifact_path, expected_hash):
        print(f"Error: Artifact hash mismatch. Expected {expected_hash}")
        sys.exit(1)

    # Build manifest
    training_data_hash = model_card.get("training_data_hash", "unknown")
    model_version = model_card.get("model_version", "unknown")
    manifest = build_manifest(
        model_version=model_version,
        approach="transformer",
        artifact_sha256=expected_hash,
        training_data_hash=training_data_hash,
        source_artifact_path=str(artifact_path),
        minio_object_key=f"{minio_bucket}/classifiers/transformer/{model_version}/manifest.json",
    )

    # Save manifest locally
    manifest_path = str(artifact_path / "manifest.json")
    save_manifest(manifest, manifest_path)
    print(f"Manifest saved to {manifest_path}")
    print(f"Artifact validated: {expected_hash}")
    print(f"Model version: {model_version}")


if __name__ == "__main__":
    upload_classifier_artifact_manifest()
