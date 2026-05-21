"""Check eval thresholds are non-zero and enabled."""

from scripts.ci.common import fail, pass_gate
from scripts.ci.thresholds import load_thresholds, validate_thresholds_nonzero


if __name__ == "__main__":
    data = load_thresholds()
    errors = validate_thresholds_nonzero(data)
    if errors:
        fail(f"Threshold validation failed: {'; '.join(errors)}")
    pass_gate(f"Thresholds: all non-zero and enabled ({len(data.get('classifier', {}))} + {len(data.get('rag', {}))} metrics)")
