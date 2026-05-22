"""Tests for model artifact hash validation gate."""

import hashlib
import json
import tempfile
from pathlib import Path

from scripts.ci.model_artifacts import compute_sha256, verify_artifact, verify_model_card


class TestModelArtifactHashGate:
    """Verify model artifact hash validation detects missing/corrupted artifacts."""

    def test_compute_sha256_deterministic(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"hello world")
            tmp = Path(f.name)
        try:
            h1 = compute_sha256(tmp)
            h2 = compute_sha256(tmp)
            assert h1 == h2
        finally:
            tmp.unlink(missing_ok=True)

    def test_verify_artifact_matching_hash(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            content = b"test artifact content"
            f.write(content)
            tmp = Path(f.name)
        try:
            expected = hashlib.sha256(content).hexdigest()
            assert verify_artifact(tmp, expected) is True
        finally:
            tmp.unlink(missing_ok=True)

    def test_verify_artifact_mismatched_hash(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"original content")
            tmp = Path(f.name)
        try:
            assert verify_artifact(tmp, "badhash123") is False
        finally:
            tmp.unlink(missing_ok=True)

    def test_verify_artifact_missing_file(self):
        assert verify_artifact(Path("/nonexistent/model.pt"), "abc123") is False

    def test_verify_model_card_valid(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as card_file:
            card_file.write(json.dumps({"artifacts": []}))
            card_path = Path(card_file.name)

        with tempfile.TemporaryDirectory() as artifacts_base:
            ok, errors = verify_model_card(card_path, Path(artifacts_base))
            assert ok is False
            assert "No artifacts" in errors[0]

        card_path.unlink(missing_ok=True)

    def test_verify_model_card_with_artifacts(self):
        import shutil
        import tempfile

        test_dir = Path(tempfile.mkdtemp())
        try:
            art_content = b"test model weights"
            art_path = test_dir / "model.pt"
            art_path.write_bytes(art_content)
            art_hash = hashlib.sha256(art_content).hexdigest()

            card_path = test_dir / "model_card.json"
            card_path.write_text(
                json.dumps(
                    {
                        "model_version": "0.1.0",
                        "artifacts": [{"path": "model.pt", "sha256": art_hash}],
                    }
                )
            )

            ok, errors = verify_model_card(card_path, test_dir)
            assert ok is True
            assert errors == []
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_verify_model_card_hash_mismatch(self):
        import shutil
        import tempfile

        test_dir = Path(tempfile.mkdtemp())
        try:
            art_content = b"test model weights"
            art_path = test_dir / "model.pt"
            art_path.write_bytes(art_content)

            card_path = test_dir / "model_card.json"
            card_path.write_text(
                json.dumps(
                    {
                        "model_version": "0.1.0",
                        "artifacts": [{"path": "model.pt", "sha256": "wrong_hash_1234567890"}],
                    }
                )
            )

            ok, errors = verify_model_card(card_path, test_dir)
            assert ok is False
            assert any("mismatch" in e.lower() for e in errors)
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_verify_model_card_missing_artifact(self):
        import shutil
        import tempfile

        test_dir = Path(tempfile.mkdtemp())
        try:
            card_path = test_dir / "model_card.json"
            card_path.write_text(
                json.dumps(
                    {
                        "model_version": "0.1.0",
                        "artifacts": [{"path": "nonexistent.pt", "sha256": "abc123"}],
                    }
                )
            )

            ok, errors = verify_model_card(card_path, test_dir)
            assert ok is False
            assert any("missing" in e.lower() for e in errors)
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_verify_model_card_file_not_found(self):
        ok, errors = verify_model_card(Path("/nonexistent/card.json"), Path("."))
        assert ok is False
        assert "not found" in errors[0]

    def test_model_artifacts_no_paid_credentials(self):
        content = Path("scripts/ci/check_model_artifacts.py").read_text()
        assert "AZURE_OPENAI_KEY" not in content
