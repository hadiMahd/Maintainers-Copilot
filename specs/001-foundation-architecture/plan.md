# Implementation Plan: Foundation and Architecture Skeleton

**Branch**: `001-foundation-architecture` | **Date**: 2026-05-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-foundation-architecture/spec.md`

## Summary

Create the Phase 1 foundation for Maintainer's Copilot: a production-shaped
repository skeleton with a startable FastAPI backend, app factory, lifespan,
typed settings, dependency injection, structured logging, request IDs, domain
exceptions, health checks, async database session wiring, Alembic baseline,
Docker Compose infrastructure, safe local configuration, baseline docs, and
critical tests. Future-phase behavior remains absent or explicitly skeletal.

## Technical Context

**Language/Version**: Python 3.11 or newer  
**Primary Dependencies**: FastAPI, pydantic-settings, SQLAlchemy async, asyncpg,
Alembic, PostgreSQL 16 with pgvector, Redis 7, MinIO, Vault dev mode, Docker
Compose, uv, ruff, pytest, httpx  
**Storage**: PostgreSQL 16 with pgvector for future persistence; Redis, MinIO,
and Vault represented as local infrastructure dependencies  
**Testing**: pytest, httpx-based ASGI tests, ruff lint and format checks  
**Target Platform**: Local Linux/container development environment  
**Project Type**: Web-service foundation with supporting model-server, chatbot,
widget, and host-demo skeleton areas  
**Performance Goals**: Backend process imports without heavy side effects; local
stack validation completes from a clean checkout; health checks remain shallow
and bounded  
**Constraints**: Phase 1 only; no ML, RAG, auth, memory, real chatbot, or widget
implementation; no expensive resources at import time or per request; no real
secrets in repository files; no blocking I/O in async request paths  
**Scale/Scope**: Single-student bootcamp project foundation that future phases can
extend without changing architectural ownership boundaries

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Gate

- **Phase Scope**: PASS. The plan implements only `PLAN.md` Phase 1 and keeps
  issue ingestion, classifier, RAG, auth, memory, chatbot orchestration, Streamlit
  UI, widget behavior, and final CI polish out of scope.
- **Layered Architecture**: PASS. The source layout preserves `app/api`,
  `app/services`, `app/repositories`, `app/domain`, `app/infra`, and
  `app/core`; routes stay HTTP-only and services/repositories/infra own their
  constitution-defined responsibilities.
- **FastAPI Resource Management**: PASS. The plan requires an app factory,
  lifespan-owned shared resources, and dependency injection for settings,
  request context, sessions, repositories, and services.
- **Async Safety**: PASS. Health routes remain shallow and async-safe; no
  blocking clients, sync database calls, sync LLM calls, or heavy file reads are
  allowed in async routes.
- **Secrets And Redaction**: PASS. Only fake/local bootstrap values appear in
  `.env.example`; real secrets are prohibited and repository secret checks are
  required.
- **Observability And Errors**: PASS. Structured logging, request IDs, domain
  exceptions, and structured HTTP errors are part of the foundation.
- **AI Evidence And Eval Gates**: PASS. No AI decisions are made in Phase 1; docs
  reserve future `DECISIONS.md` and `EVALS.md` sections.
- **Critical Tests And CI**: PASS. Critical tests are required for settings,
  health checks, structured error responses, import side effects, route boundary
  rules, and secret hygiene.
- **Simplicity**: PASS. The plan avoids multi-agent workflows and avoids heavy
  infrastructure beyond the stack required by `PLAN.md`.

### Post-Design Recheck

- **Phase Scope**: PASS. Generated contracts cover only health and structured
  errors; quickstart validates only Phase 1 behavior.
- **Layered Architecture**: PASS. `data-model.md` assigns Configuration Profile,
  Health Status, Request Context, Domain Error, Migration Baseline, Documentation
  Set, and Service Definition ownership without adding future behavior.
- **FastAPI Resource Management**: PASS. Research and quickstart reinforce app
  factory, lifespan, dependency injection, and no import-time heavy resources.
- **Async Safety**: PASS. Contracts require shallow health responses and bounded
  readiness behavior.
- **Secrets And Redaction**: PASS. Research and quickstart include fake-value
  configuration and no real secret validation.
- **Observability And Errors**: PASS. Contracts define request ID propagation and
  stable structured errors.
- **AI Evidence And Eval Gates**: PASS. No AI eval gates are introduced in this
  phase.
- **Critical Tests And CI**: PASS. Quickstart and generated artifacts call out
  tests for critical Phase 1 behavior.
- **Simplicity**: PASS. No complexity exceptions were introduced.

## Project Structure

### Documentation (this feature)

```text
specs/001-foundation-architecture/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── health-and-errors.openapi.yaml
└── tasks.md              # Created by /speckit.tasks, not by /speckit.plan
```

### Source Code (repository root)

```text
app/
├── api/
│   ├── dependencies/
│   ├── middleware/
│   └── routes/
├── services/
├── repositories/
├── domain/
├── infra/
└── core/

migrations/
scripts/
tests/
├── contract/
├── integration/
└── unit/
docs/
prompts/
evals/
data/
├── raw/
└── processed/
artifacts/
model_server/
chatbot/
widget/
demo/
└── host/
```

**Structure Decision**: Use the constitution's explicit app-layer structure with
`app/core` for cross-cutting settings, logging, error registration, request
context, and application creation. Keep `app/api` HTTP-only, `app/services`
workflow-only, `app/repositories` persistence-only, `app/domain` for Pydantic
domain/error/health models, and `app/infra` for external adapters. Use
`migrations/` for Alembic. Keep model server, chatbot, widget, and host demo as
skeleton areas only.

## Complexity Tracking

No constitution violations or complexity exceptions.
