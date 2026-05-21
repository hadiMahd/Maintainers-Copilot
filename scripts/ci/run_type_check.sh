#!/usr/bin/env bash
set -euo pipefail
echo "=== Type-check gate (mypy) ==="
uv run mypy .
echo "Gate: type-check PASSED"
