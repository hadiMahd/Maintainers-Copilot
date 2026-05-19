# Architecture

## Layer Ownership Table

| Layer | Directory | Owns | Forbidden From |
|---|---|---|---|
| api | `app/api/` | HTTP routing, dependency wiring, request parsing, response mapping | SQLAlchemy, Redis, hvac, minio, httpx direct calls |
| services | `app/services/` | Business workflows, transaction boundaries, cache invalidation | SQLAlchemy sessions, Redis clients, external HTTP calls |
| repositories | `app/repositories/` | SQL and persistence only | Business logic, workflow orchestration |
| domain | `app/domain/` | Pydantic domain models, errors | Imports from `app/infra/` or `app/core/` |
| infra | `app/infra/` | Adapters for Vault, MinIO, Redis, DB, external APIs | Business logic, route handling |
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

## Extension Points

- New routes: add files under `app/api/routes/` and register them at the bottom of each route module by importing `app` from `app.core.application`.
- New services: add files under `app/services/`.
- New repositories: add files under `app/repositories/`.
- New infra adapters: add files under `app/infra/`.
