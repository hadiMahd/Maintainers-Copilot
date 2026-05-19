# Runbook

## Start Stack

```bash
cp .env.example .env
docker compose up --wait
```

## Stop Stack

```bash
docker compose down -v
```

## Run Tests

```bash
uv run pytest tests/ -v
```

## Run Migrations

```bash
DATABASE_URL=postgresql+asyncpg://maintainer:maintainer@localhost:5432/maintainer uv run alembic upgrade head
```

## Check Health

```bash
curl -s localhost:8000/health/live | jq .
curl -s localhost:8000/health/ready | jq .
```

## Common Failures

- **Vault unreachable**: check `VAULT_ADDR`, run `docker compose ps vault`
- **Postgres unhealthy**: check `docker compose logs postgres`
- **pgvector not installed**: run `docker compose restart migrations`
- **Backend crash on startup**: Vault auth failure — check `VAULT_TOKEN` and `docker compose logs vault_seed`

## Start Model Server

```bash
CLASSIFIER_ARTIFACT_DIR=artifacts/classifiers/classical \
CLASSIFIER_MODEL_VERSION=0.1.0 \
uv run uvicorn model_server.main:app --port 8001
```

## Check Model Server Health

```bash
curl -s localhost:8001/health | jq .
```

## Measure Classifier Latency

```bash
uv run python scripts/measure_classifier_latency.py
```

Expected: P95 ≤ 500ms for 30 sequential warm requests.

## Classifier Endpoint Unavailable

If the model server returns 503 with `classifier_model_unavailable`:
- Check `CLASSIFIER_ARTIFACT_DIR` points to a valid artifact directory
- Verify `model_card.json` exists in the artifact directory
- Check artifact hash matches model card `artifact_sha256`
- Verify the model was loaded during startup (check startup logs)
