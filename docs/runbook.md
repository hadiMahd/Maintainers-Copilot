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
- **Backend crash on startup**: Vault auth failure — check `VAULT_ROLE_ID` / `VAULT_SECRET_ID`
