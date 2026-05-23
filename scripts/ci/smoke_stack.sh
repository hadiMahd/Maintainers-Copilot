#!/usr/bin/env bash
set -euo pipefail
echo "=== Stack smoke test ==="
echo "Starting full production-functional stack including model_server..."
echo ""

if ! command -v docker &>/dev/null; then
    echo "SKIP: Docker not available"
    exit 0
fi

echo "Step 1: Building images..."
docker compose build --quiet 2>&1 | tail -3

echo ""
echo "Step 2: Starting services (postgres, redis, minio, vault, model_server, backend)..."
docker compose up -d postgres redis minio vault model_server backend 2>&1

echo ""
echo "Step 3: Waiting for backend health..."
MAX_WAIT=60
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -sf http://localhost:8000/health/live > /dev/null 2>&1; then
        echo "Backend health endpoint reached after ${WAITED}s"
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "ERROR: Backend health endpoint not reached within ${MAX_WAIT}s"
    docker compose logs --tail 20 backend model_server
    docker compose down -v 2>/dev/null
    exit 1
fi

echo ""
echo "Stack smoke test PASSED"
docker compose down -v 2>/dev/null
