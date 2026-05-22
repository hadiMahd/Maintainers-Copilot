#!/usr/bin/env bash
set -euo pipefail
echo "=== Type-check gate (mypy on scripts/ci) ==="
uv run mypy scripts/ci/ --explicit-package-bases
echo "Gate: type-check PASSED"
