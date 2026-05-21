#!/usr/bin/env bash
set -euo pipefail
echo "=== Format check gate (black) ==="
uv run black --check .
echo "=== Import-order gate (isort) ==="
uv run isort --check-only .
echo "Gate: format-check PASSED"
