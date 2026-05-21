"""Check model artifact hashes against model cards."""

from scripts.ci.common import fail, pass_gate
from scripts.ci.model_artifacts import verify_model_card
from pathlib import Path


if __name__ == "__main__":
    card_dir = Path("artifacts/evals")
    card_path = card_dir / "model_card.json"
    if not card_path.exists():
        pass_gate("Model artifacts: no model card found (stub - full check in US3)")
    else:
        ok, errors = verify_model_card(card_path, Path("artifacts"))
        if not ok:
            fail(f"Model artifact: {len(errors)} error(s): {'; '.join(errors[:5])}")
        pass_gate("Model artifacts: verified")
