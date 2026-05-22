"""Static secret pattern scanner for unsafe sk- and password patterns.

Scans the entire repository for committed secret-like patterns using the
secret_scan.py helper. Allowlisted files (secret_scan.py itself, .flake8,
constitution.md, etc.) are excluded from failure but still reported for
auditability.

Unsafe patterns detected:
  - sk- (OpenAI-style API key prefix)
  - password= (hardcoded password assignment)
  - passwd= (hardcoded password variant)
  - SECRET_KEY= (hardcoded secret key)
"""

import sys
from pathlib import Path

from scripts.ci.common import fail, pass_gate, safe_summary
from scripts.ci.secret_scan import UNSAFE_PATTERNS, is_allowlisted, scan_directory

if __name__ == "__main__":
    print(f"Scanning repository for {len(UNSAFE_PATTERNS)} unsafe patterns...")
    hits = scan_directory(Path("."))

    non_allowlisted: list[tuple[Path, int, str, str]] = []
    allowlisted_hits: list[tuple[Path, int, str, str]] = []

    for path, lineno, pattern, snippet in hits:
        if is_allowlisted(path, pattern, snippet):
            allowlisted_hits.append((path, lineno, pattern, snippet))
        else:
            non_allowlisted.append((path, lineno, pattern, snippet))

    if allowlisted_hits:
        print(f"  {len(allowlisted_hits)} allowlisted hit(s) in known-safe files:")
        for path, lineno, pattern, _ in allowlisted_hits[:5]:
            print(f"    {path}:{lineno} [{pattern}]")

    if non_allowlisted:
        safe = safe_summary(
            [f"{p}:{l} [{pat}]" for p, l, pat, _ in non_allowlisted[:10]],
            max_lines=10,
        )
        fail(
            f"Static secret grep: {len(non_allowlisted)} unsafe pattern(s) "
            f"in {len(set(p for p, _, _, _ in non_allowlisted))} file(s):\n{safe}"
        )
        sys.exit(1)

    pass_gate(
        f"Static secret grep: clean — {len(hits)} total hits, "
        f"{len(allowlisted_hits)} allowlisted, 0 unsafe"
    )
