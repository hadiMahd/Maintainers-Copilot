# Architecture

## Layer Ownership Table

| Layer | Directory | Owns | Forbidden From |
|---|---|---|---|
| api | `app/api/` | HTTP routing, dependency wiring, request parsing, response mapping | SQLAlchemy, Redis, hvac, minio, httpx direct calls |
| services | `app/services/` | Business workflows, transaction boundaries, cache invalidation | SQLAlchemy sessions, Redis clients, external HTTP calls |
| repositories | `app/repositories/` | SQL and persistence only | Business logic, workflow orchestration |
| domain | `app/domain/` | Pydantic domain models, errors | Imports from `app/infra/` or `app/core/` |
| infra | `app/infra/` | Adapters for Vault, MinIO, Redis, DB, external APIs, LLM, MLflow, redaction | Business logic, route handling |
| core | `app/core/` | Application factory, config, lifespan, logging, middleware | No forbidden targets; serves as cross-cutting layer |

## Dependency Flow

Allowed call directions:

- `api` → `services` → `repositories` → `domain`
- `infra` → `domain`
- `core` → all layers

Routes may not call SQLAlchemy, Redis, hvac, minio, or httpx directly. They must call `app/services/` functions only.

## Guardrails

1. **Route Isolation**: `app/api/` handlers must never import or call SQLAlchemy, Redis, hvac, minio, or httpx directly. They call `app/services/` functions only.
2. **Domain Purity**: `app/domain/` has no imports from `app/infra/` or `app/core/`.
3. **No Import Side Effects**: No module may make network connections at import time.
4. **Structured Logging**: All log output is JSON via structlog with `request_id` bound via contextvars.
5. **Error Shape**: Every error response is `{error_code, message, request_id}` with no stack traces.

## Model Server Architecture

The model server is a separate FastAPI application in `model_server/` that loads a classifier artifact during lifespan and serves predictions.

### Model Server Layers

| Layer | Directory | Owns | Forbidden From |
|---|---|---|---|
| api | `model_server/api/` | HTTP routing, request parsing, response mapping | Direct model loading, file I/O |
| services | `model_server/services/` | Inference orchestration, input-size checks | File I/O, direct adapter calls |
| infra | `model_server/infra/` | Artifact loading, hash validation | Route handling |
| domain | `model_server/domain/` | Prediction and error schemas | Imports from infra |

### Classifier Endpoint

- **POST /classifier/predict**: Accepts title, body, and/or comments. Returns a typed label (`bug`, `feature`, `docs`, `question`), optional confidence, and semantic `model_version`.
- **Model loading**: The classifier artifact is loaded once during FastAPI lifespan, never at import time or per request.
- **Unavailable model**: Returns 503 with `classifier_model_unavailable` error code and a structured reason (`missing_artifact`, `invalid_artifact`, `hash_mismatch`, `startup_load_failed`). No stack traces are exposed.
- **Input limits**: Title ≤ 512 chars, body ≤ 16,000 chars, comments ≤ 100 items, each comment ≤ 4,000 chars.
- **Latency target**: P95 ≤ 500ms for one request on a warm, preloaded, single-process model-server measured across 30 sequential representative requests.

## Extension Points

- New routes: add files under `app/api/routes/` and register them at the bottom of each route module by importing `app` from `app.core.application`.
- New services: add files under `app/services/`.
- New repositories: add files under `app/repositories/`.
- New infra adapters: add files under `app/infra/`.
