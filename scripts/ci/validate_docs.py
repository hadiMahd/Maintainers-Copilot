"""Validate documentation completeness."""

from scripts.ci.common import fail, pass_gate
from scripts.ci.docs_check import validate_all_docs


if __name__ == "__main__":
    passed, results = validate_all_docs()
    for name, status in results.items():
        print(f"  {name}: {status}")
    if not passed:
        failures = [f"{k}: {v}" for k, v in results.items() if v != "PASS"]
        fail(f"Docs validation: {len(failures)} failure(s): {'; '.join(failures[:3])}")
    pass_gate("Docs validation: all required docs present")
