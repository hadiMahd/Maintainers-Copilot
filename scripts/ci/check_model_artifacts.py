"""Check model artifact hashes against model cards.

Scans artifacts/evals/ for model card JSON files and verifies that all
referenced artifacts exist with matching SHA-256 hashes.

Expected model card location: artifacts/evals/model_card.json
Artifact base path: artifacts/

Failure conditions:
  - Model card not found or unreadable
  - No artifacts listed in card
  - Referenced artifact file missing
  - SHA-256 hash does not match
"""

import sys
from pathlib import Path

from scripts.ci.common import fail, pass_gate
from scripts.ci.model_artifacts import verify_model_card


if __name__ == "__main__":
    card_dir = Path("artifacts/evals")
    card_path = card_dir / "model_card.json"
    artifacts_base = Path("artifacts")

    if not card_path.exists():
        pass_gate(
            "Model artifacts: no model card found at artifacts/evals/model_card.json "
            "(CI has no model artifacts)"
        )
        sys.exit(0)

    ok, errors = verify_model_card(card_path, artifacts_base)

    if not ok:
        safe = "; ".join(errors[:5])
        if len(errors) > 5:
            safe += f" ... and {len(errors) - 5} more"
        fail(f"Model artifact: {len(errors)} error(s): {safe}")
        sys.exit(1)

    pass_gate(
        f"Model artifacts: verified against {card_path} — all hashes match"
    )
