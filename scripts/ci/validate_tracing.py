"""Validate tracing configuration."""

from scripts.ci.common import fail, pass_gate
from scripts.ci.tracing_checks import check_tracing_enabled_warning


if __name__ == "__main__":
    ok, msg = check_tracing_enabled_warning()
    if not ok:
        fail(f"Tracing config: {msg}")
    pass_gate(f"Tracing config: {msg}")
