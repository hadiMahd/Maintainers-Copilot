#!/usr/bin/env bash
set -euo pipefail
echo "=== Test gate (pytest) ==="
uv run pytest "$@"
echo "Gate: test PASSED"
