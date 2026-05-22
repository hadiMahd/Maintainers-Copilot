#!/usr/bin/env bash
set -euo pipefail
echo "=== Type-check gate (mypy on app + scripts/ci) ==="
uv run mypy app/ scripts/ci/ --explicit-package-bases
echo "Gate: type-check PASSED"
