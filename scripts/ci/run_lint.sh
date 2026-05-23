#!/usr/bin/env bash
set -euo pipefail
echo "=== Lint gate (flake8) ==="
uv run flake8 .
echo "Gate: lint PASSED"
