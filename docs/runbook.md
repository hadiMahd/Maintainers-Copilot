# Runbook

## Start Stack

```bash
cp .env.example .env
docker compose up -d vault postgres redis minio
uv run python scripts/seed_vault_from_env.py .env
docker compose up -d migrations backend
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
- **Backend crash on startup**: secrets may not be seeded yet — re-run `uv run python scripts/seed_vault_from_env.py .env`, then `docker compose restart backend`

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

## Ingest RAG Corpus

```bash
uv run python scripts/ingest_docs.py
uv run python scripts/ingest_resolved_issues.py --input /path/to/issues.jsonl
```

Expected: `data/processed/rag_doc_sources.jsonl`, `rag_issue_answer_sources.jsonl`, and `rag_chunks.jsonl` created.

## Build RAG Index

```bash
uv run python scripts/build_rag_index.py
```

For testing without real embeddings:
```bash
uv run python scripts/build_rag_index.py --fake
```

Expected: `artifacts/rag/embedding_comparison.json` created with both embedding candidates recorded.

## Evaluate RAG Pipeline

```bash
uv run python scripts/evaluate_rag.py --exploratory
```

Expected: `evals/rag_eval_report.json` created with baseline-vs-advanced comparison, judge_id, embedding comparison, and disagreement notes.

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
