"""Static secret pattern scanner for unsafe API key and password patterns."""

from scripts.ci.common import fail, pass_gate
from scripts.ci.secret_scan import scan_directory, is_allowlisted
from pathlib import Path


if __name__ == "__main__":
    hits = scan_directory(Path("."))
    real_hits = [(p, l, pat, s) for p, l, pat, s in hits if not is_allowlisted(p, pat, s)]
    if real_hits:
        summary = "; ".join(f"{p}:{l}" for p, l, _, _ in real_hits[:5])
        fail(f"Static secret grep: {len(real_hits)} unsafe pattern(s): {summary}")
    pass_gate("Static secret grep: clean (stub - full check in US3)")
