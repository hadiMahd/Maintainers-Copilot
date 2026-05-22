"""Model artifact hash helper functions."""

import hashlib
from pathlib import Path


def compute_sha256(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_artifact(artifact_path: Path, expected_sha256: str) -> bool:
    """Verify that an artifact exists and matches its expected SHA-256."""
    if not artifact_path.exists():
        return False
    actual = compute_sha256(artifact_path)
    return actual == expected_sha256


def verify_model_card(
    card_path: Path,
    artifacts_base: Path,
) -> tuple[bool, list[str]]:
    """Verify all artifacts referenced in a model card exist and match hashes."""
    import json

    errors: list[str] = []
    if not card_path.exists():
        errors.append(f"Model card not found: {card_path}")
        return False, errors

    try:
        with open(card_path) as f:
            card = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        errors.append(f"Failed to read model card: {e}")
        return False, errors

    artifacts = card.get("artifacts", [])
    if not artifacts:
        errors.append("No artifacts listed in model card")
        return False, errors

    all_ok = True
    for art in artifacts:
        path_str = art.get("path", "")
        expected = art.get("sha256", "")
        if not path_str or not expected:
            errors.append(f"Artifact missing path or sha256: {art}")
            all_ok = False
            continue
        artifact_path = artifacts_base / path_str
        if not artifact_path.exists():
            errors.append(f"Artifact missing: {artifact_path}")
            all_ok = False
            continue
        actual = compute_sha256(artifact_path)
        if actual != expected:
            errors.append(
                f"Hash mismatch for {path_str}: expected {expected[:12]}..., got {actual[:12]}..."
            )
            all_ok = False

    return all_ok, errors
