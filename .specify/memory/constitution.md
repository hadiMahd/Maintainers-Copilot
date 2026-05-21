<!--
Sync Impact Report
Version change: 1.0.0 -> 1.0.1
Modified principles:
- VIII. AI Decisions Require Numbers: clarified canonical decisions record path
  as docs/decisions.md
Added sections:
- None
Removed sections:
- None
Templates requiring updates:
- ✅ updated: .specify/templates/plan-template.md
- ✅ updated: .specify/templates/spec-template.md
- ✅ updated: .specify/templates/tasks-template.md
- ✅ checked: .specify/templates/checklist-template.md (no decision path reference)
- ✅ checked: .specify/extensions/git/commands/*.md (no decision path reference)
- ✅ checked: .agents/skills/speckit-tasks/SKILL.md (no decision path reference)
- ✅ checked: README.md (already links docs/decisions.md)
Follow-up TODOs:
- None
-->
# Maintainer's Copilot Constitution

## Core Principles

### I. Architecture Is Part Of The Grade
Maintainer's Copilot MUST maintain clean application layers. `app/api` MUST contain
HTTP routing, dependency wiring, request parsing, and response mapping only.
`app/services` MUST own business workflows, transaction boundaries, cache
invalidation, and memory invalidation. `app/repositories` MUST own SQL and
persistence only. `app/domain` MUST contain Pydantic domain models distinct from
ORM models. `app/infra` MUST contain adapters for Vault, MinIO, Redis, LLM
providers, model servers, tracing, redaction, and external APIs. Routers MUST NOT
touch SQLAlchemy, Redis, Vault, MinIO, LLM clients, model clients, or other
external systems directly.

Rationale: The project is graded on architecture, and clean boundaries keep the
solo codebase explainable, testable, and defensible line by line.

### II. FastAPI Resource Management
The backend MUST use an app factory and FastAPI lifespan for expensive shared
resources, including database engines, Redis clients, Vault clients, LLM clients,
model clients, and model artifacts. FastAPI dependency injection MUST provide
settings, database sessions, repositories, services, current user, external
clients, and request context. The codebase MUST NOT create models, clients,
engines, external connections, or expensive resources at import time or per
request.

Rationale: Startup ownership and dependency injection make resource lifetimes
auditable and prevent hidden side effects during imports, tests, and requests.

### III. Non-Blocking Async Paths
Async request paths MUST NOT call `requests`, `time.sleep`, synchronous database
clients, synchronous LLM calls, or large synchronous file reads. HTTP, database,
Redis, LLM, and model-server calls in async paths MUST use async clients with
explicit timeouts. CPU-heavy or blocking work MUST move to scripts, jobs, model
server startup, or `asyncio.to_thread` with a documented reason.

Rationale: A production-shaped FastAPI service must keep its event loop
available and make latency failures bounded.

### IV. Secret Hygiene And Vault Resolution
Real secrets MUST NOT be committed. `.env` files MAY contain only local bootstrap
values such as Vault token and local ports. API keys, JWT signing keys, database
passwords, MinIO credentials, tracing keys, and LLM keys MUST resolve from Vault
or test fakes at startup. Seed scripts, notebooks, docs, tests, and fixtures MUST
NOT contain real credentials.

Rationale: Secret handling is a release blocker because one committed credential
invalidates the safety of the project.

### V. Structured Observability
Application code MUST use structured logs and MUST NOT use `print` statements.
Logs and traces MUST carry `request_id` and `trace_id` where relevant. Every LLM
call, tool call, and RAG retrieval MUST be traced. Logs and traces MUST be
joinable enough to reconstruct a request path without exposing sensitive
payloads.

Rationale: The maintainer assistant cannot be debugged or reviewed reliably
without traceable AI, tool, retrieval, and API behavior.

### VI. Redaction Before Persistence Or Telemetry
A redaction layer in `app/infra` MUST run before logs, traces, audit metadata,
and memory writes. Raw prompts, issue bodies, tool payloads, secrets, and
credentials MUST NOT be emitted unredacted. Tests MUST prove fake secrets do not
appear unredacted in logs, traces, audit records, or memory.

Rationale: The system processes user text, issue content, and provider secrets;
redaction must be centralized and test-proven before data leaves the workflow.

### VII. Clean Errors At The Boundary
Domain failures MUST use a domain exception hierarchy. API boundaries MUST map
domain exceptions to structured HTTP errors with stable error codes. Users MUST
NOT receive stack traces. Unexpected exceptions MUST be logged with `request_id`
and `trace_id`, then returned as structured server errors.

Rationale: Clean errors keep user behavior predictable while preserving enough
diagnostic context for maintainers.

### VIII. AI Decisions Require Numbers
Classifier choice, embedding model choice, chunking strategy, retrieval
weighting, reranking, RAG generation behavior, memory type, and tracing backend
MUST be backed by evaluation numbers or documented constraints. `docs/decisions.md`
MUST record the selected option, measured results, rejected alternatives, and the
reason the chosen option is acceptable for the bootcamp scope.

Rationale: AI components must be chosen through evidence, not preference or
demo-only behavior.

### IX. Evals Are Release Gates
Classification and RAG golden sets MUST exist before those capabilities are
treated as complete. `eval_thresholds.yaml` MUST contain non-zero thresholds.
CI MUST fail when classifier or RAG results regress below committed thresholds,
when eval thresholds are zeroed, when fake secrets leak unredacted, or when model
artifact hashes do not match their model cards.

Rationale: A maintainer copilot is only production-shaped when regressions are
machine-detectable.

### X. Controlled Scope And Single LLM
Each Spec Kit phase MUST implement only the current phase scope from `PLAN.md`.
Future-phase behavior MUST remain absent or clearly stubbed with a later-phase
reference. The chatbot MUST use one tool-calling LLM and MUST NOT become a
multi-agent system. The project MUST NOT add product features beyond the Week 7
requirements, and MUST prefer explicit, boring code over clever abstractions.

Rationale: The project is a solo bootcamp deliverable; controlled scope protects
architecture quality, schedule, and reviewability.

## Project Constraints

The default backend stack is Python 3.11 or newer, FastAPI, pydantic-settings,
SQLAlchemy async, asyncpg, Alembic, PostgreSQL 16 with pgvector, Redis 7, MinIO,
Vault dev mode, Docker Compose, uv, ruff, pytest, and httpx. Streamlit is an
internal UI only. The embedded widget is a Vite React widget delivered through a
loader script and iframe isolation. Model training, ingestion, embedding, and
evaluation MUST run through reproducible scripts or CI jobs, not through API
request paths.

Repository structure MUST preserve the phase-ready directories described in
`PLAN.md`: `app/api`, `app/services`, `app/repositories`, `app/domain`,
`app/infra`, `tests`, `scripts`, `docs`, `prompts`, `evals`, `data/raw`,
`data/processed`, `artifacts`, `model_server`, `chatbot`, `widget`, and
`demo/host`. New infrastructure such as Kafka, Kubernetes, Celery, or additional
datastores MUST NOT be added unless a current phase cannot meet its acceptance
criteria without it and the complexity is recorded in the implementation plan.

## Development Workflow

Work MUST proceed one Spec Kit phase at a time from `PLAN.md`. Every feature spec
MUST state its current phase, explicit out-of-scope items, independent user
stories, measurable success criteria, and security, observability, and eval
requirements when applicable. Every implementation plan MUST complete the
Constitution Check before design work and again after design work.

Tasks MUST be dependency ordered and include exact file paths. Tests are
mandatory for critical behavior, including settings, health checks, errors,
architecture boundaries, redaction, auth, memory, eval metrics, retrieval
schemas, model-server contracts, widget origin checks, and CI gates. Documentation
updates are mandatory when a phase makes architectural, security, AI, eval,
memory, or operational decisions. `/speckit.analyze` MUST run before
implementation and any critical constitution violation MUST be fixed in the
spec, plan, or tasks before coding continues.

## Governance

This constitution supersedes conflicting project guidance. Amendments MUST update
this file, include a Sync Impact Report, identify affected templates and runtime
guidance, and explain the version bump. Amendments that remove or redefine a
principle require a MAJOR version bump. New principles or materially expanded
governance require a MINOR version bump. Clarifications that do not change
behavior require a PATCH version bump.

Every feature review MUST verify compliance with the Core Principles, Project
Constraints, and Development Workflow. Unjustified violations of architecture,
secret hygiene, redaction, non-blocking async paths, clean errors, or eval gates
are release blockers. Any accepted complexity exception MUST be documented in the
plan's Complexity Tracking table with the simpler alternative that was rejected.

**Version**: 1.0.1 | **Ratified**: 2026-05-18 | **Last Amended**: 2026-05-20
