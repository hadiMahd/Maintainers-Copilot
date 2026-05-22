# Maintainer's Copilot

AI-powered maintainer assistant for open-source projects.

## Prerequisites / Installation

- Docker Desktop / Docker Engine
- `uv` (Python package manager)
- Vault CLI (optional for local secret management)

Install dependencies:
```bash
uv sync --all-extras --dev
```

## Quick Start

1. `git clone <repo> && cd maintainer-copilot`
2. `uv sync`
3. `cp .env.example .env`
4. Fill `.env` seed values, especially Azure OpenAI and LangSmith values.
5. `docker compose up -d`
6. `curl -s localhost:8000/health/live`
7. `curl -s localhost:8000/health/ready`

## Architecture Overview

Clean layered architecture with `app/api`, `app/services`, `app/repositories`, `app/domain`, `app/infra`, and `app/core`.
See [docs/architecture.md](docs/architecture.md) for full details.

## Available Commands

| Command | Description |
|---|---|
| `uv run pytest` | Run the test suite |
| `make validate` | Run full validation workflow (all gates) |
| `make lint` | Run flake8 lint checks |
| `make format-check` | Run black + isort format checks |
| `make import-check` | Run isort import-order check |
| `make type-check` | Run mypy type checking |
| `make test` | Run pytest test suite |
| `make evals` | Run eval gates (thresholds, classifier, RAG) |
| `make security` | Run security gates (redaction, grep, artifacts, startup, tracing) |
| `make smoke` | Run full-stack smoke test |
| `make docs` | Validate documentation completeness |
| `uv run alembic upgrade head` | Run database migrations |
| `uv run python scripts/seed_vault_from_env.py .env` | Manually seed local Vault from `.env` |
| `python scripts/validate_stack.py` | Validate local stack prerequisites |
| `docker compose up -d` | Start the full local stack |

### CI & Validation

The project includes a GitHub Actions CI workflow (`.github/workflows/ci.yml`) and a
`Makefile` for local gate orchestration. Both paths produce equivalent pass/fail
results.

**Run the full validation workflow locally**:
```bash
make validate
```

**Run the full-stack smoke test**:
```bash
make smoke
```
This starts the production-functional Docker Compose stack (postgres, redis, minio,
vault, vault_seed, model_server, backend) and verifies the backend health endpoint responds.

**Individual gate commands**:
```bash
make lint          # flake8
make format-check  # black + isort
make import-check  # isort only
make type-check    # mypy
make test          # pytest
make evals         # threshold + classifier + RAG eval gates
make security      # redaction + static grep + artifacts + startup + tracing
make docs          # documentation completeness check
```

## Demo Flow

1. Start the stack: `docker compose up -d`
2. Check API health: `curl -s localhost:8000/health/live | jq .`
3. Open Streamlit: `http://localhost:8501`
4. Run validation: `make validate`

Widget demo:
- Allowed host: `http://localhost:8080`
- Blocked host: `http://localhost:8081`
- Widget bundle static server: `http://localhost:8082`

Use the Streamlit admin page to create a widget config and allow only
`http://localhost:8080`, then set `DEMO_WIDGET_ID` in `.env` and restart
`demo_host`.

For full-stack demo with model server:
```bash
make smoke
```

### Expected Results

| Step | Expected |
|---|---|
| Health | `{"status": "ok"}` |
| `make validate` | All gates pass (lint, format, type-check, tests) |
| `make smoke` | Backend health endpoint reached |
| `make evals` | Classifier and RAG eval pass thresholds |
| `make security` | Redaction, grep, artifacts, startup, tracing pass |

## Docs

- [Architecture](docs/architecture.md)
- [Decisions](docs/decisions.md)
- [Runbook](docs/runbook.md)
- [Evals](docs/evals.md)
- [Security](docs/security.md)
