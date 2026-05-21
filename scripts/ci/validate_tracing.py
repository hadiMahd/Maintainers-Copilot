"""Validate tracing configuration.

Checks that LangSmith tracing configuration is valid for the current
environment. In CI without credentials, acknowledges that tracing is
not configured (non-fatal). In production mode with misconfigured tracing,
fails the gate.

Valid configuration requires:
  - LANGSMITH_API_KEY present and of reasonable length
  - LANGSMITH_PROJECT set when LANGSMITH_ENDPOINT is set
  - No obviously invalid key formats
"""

import sys

from scripts.ci.common import fail, pass_gate
from scripts.ci.tracing_checks import check_tracing_enabled_warning, validate_tracing_config


if __name__ == "__main__":
    passed, errors = validate_tracing_config()

    if passed:
        pass_gate("Tracing config: valid")
        sys.exit(0)

    ok, msg = check_tracing_enabled_warning()

    if not ok:
        pass_gate(
            f"Tracing config: not configured for CI (expected — no LangSmith credentials). "
            f"Issues: {'; '.join(errors[:2])}"
        )
    else:
        fail(f"Tracing config: {msg}")
