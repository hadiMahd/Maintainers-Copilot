# Feature Specification: Foundation and Architecture Skeleton

**Feature Branch**: `001-foundation-architecture`  
**Created**: 2026-05-18  
**Status**: Draft  
**Input**: User description: "Build the foundation and architecture skeleton for Maintainer's Copilot."

## Clarifications

### Session 2026-05-18

- Q: Which services should `docker compose up` start by default in Phase 1? → A: Backend, Postgres/pgvector, Redis, MinIO, Vault, and migration runner only; model-server/chatbot/widget/host demo remain skeletal or profile-gated.
- Q: Should the Phase 1 Alembic baseline create the PostgreSQL `vector` extension? → A: Yes, baseline migration enables `CREATE EXTENSION IF NOT EXISTS vector` and validates pgvector availability.
- Q: How should `/health/ready` behave when a default core dependency is unavailable? → A: Return HTTP 503 with per-check statuses when any default core dependency is unavailable; return 200 only when all default core checks pass.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start and Validate the Local Foundation (Priority: P1)

A developer setting up the project locally can use the documented bootstrap
values, validate the local service stack configuration, start the backend service,
and confirm the service is alive and shallowly ready.

**Why this priority**: This is the minimum useful foundation. Future phases cannot
build safely until a developer can run the base service and verify readiness.

**Independent Test**: From a clean checkout, a developer can follow the setup
instructions, create local configuration from the example file, validate the stack
configuration, start the service, and receive successful live and ready health
responses.

**Acceptance Scenarios**:

1. **Given** a clean checkout with only example local values, **When** the
   developer validates the local stack configuration, **Then** validation
   completes without configuration errors.
2. **Given** the backend service has started, **When** the developer checks the
   live health route, **Then** the response confirms the process is alive.
3. **Given** required local dependencies are represented in the stack, **When**
   the developer checks the ready health route, **Then** the response reports
   shallow readiness without performing expensive work.

---

### User Story 2 - Review the Architecture Boundaries (Priority: P2)

A reviewer inspecting the project can identify the intended application layers,
the ownership of each layer, the documented architecture decisions, and the
guardrails that prevent routes from owning persistence, external clients, or
future-phase behavior.

**Why this priority**: The project is graded on architecture, and reviewers need
clear evidence that the repository shape matches the constitution before feature
logic is added.

**Independent Test**: A reviewer can inspect the repository structure and
documentation and confirm that layer names, ownership rules, baseline docs, and
critical tests are present without needing classifier, RAG, chatbot, auth, or
widget functionality.

**Acceptance Scenarios**:

1. **Given** the repository skeleton exists, **When** a reviewer inspects the
   backend folders, **Then** the route, service, repository, domain, infra, and
   shared concern boundaries are clear.
2. **Given** the skeleton documentation exists, **When** a reviewer opens the
   architecture, decisions, operations, evaluation, and security docs, **Then**
   each document explains its purpose and provides a place for future phase
   decisions.
3. **Given** no future phase is in scope, **When** a reviewer searches the base
   repository, **Then** there is no implemented classifier, RAG pipeline, auth
   flow, chatbot orchestration, memory feature, or widget behavior.

---

### User Story 3 - Extend the Foundation in Later Phases (Priority: P3)

A future phase implementer can add dataset, model, RAG, auth, chatbot, UI, and
widget work into predictable locations without changing the foundational
application shape or inventing new cross-cutting patterns.

**Why this priority**: The skeleton must make later work straightforward while
keeping this phase small and production-shaped.

**Independent Test**: A future implementer can identify the correct place for a
new route, workflow service, persistence object, external adapter, script, test,
prompt, evaluation artifact, data artifact, or documentation update using the
existing structure and docs.

**Acceptance Scenarios**:

1. **Given** a later phase needs a workflow, **When** the implementer examines the
   structure, **Then** the service layer is the obvious owner of workflow and
   transaction behavior.
2. **Given** a later phase needs an external dependency, **When** the implementer
   examines the structure, **Then** the infra layer is the obvious owner of the
   adapter.
3. **Given** a later phase needs evidence or operational notes, **When** the
   implementer examines the docs, **Then** the decisions, evaluation, runbook,
   architecture, and security documents provide explicit update locations.

### Edge Cases

- Required local configuration is missing or malformed: startup fails loudly with
  a clear configuration error instead of silently using unsafe defaults.
- A developer validates readiness before a dependency is reachable: readiness
  returns HTTP 503 with per-check dependency status without crashing or doing
  heavy work.
- PostgreSQL is reachable but the pgvector extension is unavailable: migration
  or readiness validation fails clearly instead of deferring the problem to RAG
  or memory phases.
- A route raises a known domain error: the user receives a structured error
  response and no stack trace.
- A route raises an unexpected error: the user receives a structured server error
  while diagnostic context remains available to logs.
- A contributor accidentally adds real secrets or local generated artifacts:
  ignore rules and tests make the mistake visible before release.
- A contributor tries to place persistence, external client, or future-phase
  behavior in a route: architecture tests or review gates flag the violation.
- Future-facing services are present in the repository but not selected in the
  default Compose profile: the default stack still starts core infrastructure
  successfully, and optional profile startup does not claim future functionality.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The repository MUST contain the constitution-mandated foundational
  structure for routes, services, repositories, domain models, infra adapters,
  shared concerns, migrations, scripts, tests, docs, prompts, evals, data,
  artifacts, model server, chatbot, widget, and host demo areas.
- **FR-002**: The backend service MUST provide a startable application shell with
  a single creation path and no expensive work performed during module import.
- **FR-003**: The backend service MUST define startup and shutdown ownership for
  expensive shared resources so future dependencies can be initialized once and
  reused safely.
- **FR-004**: The project MUST provide typed configuration with clear required
  values, safe local examples, and loud failure when required values are missing.
- **FR-005**: The project MUST provide a default local stack that starts the
  backend, migration runner, PostgreSQL with pgvector, Redis, MinIO, and Vault.
  Model server, chatbot, widget, and host demo services MUST remain skeletal or
  profile-gated in Phase 1 and MUST NOT start by default.
- **FR-006**: The backend service MUST expose live and ready health checks that
  distinguish process liveness from shallow dependency readiness. `/health/ready`
  MUST return HTTP 200 only when all default core dependency checks pass and
  MUST return HTTP 503 with per-check statuses when any default core dependency
  is unavailable.
- **FR-007**: The backend service MUST include request correlation so each request
  can carry a request identifier through logs and error responses.
- **FR-008**: The backend service MUST provide structured logging and MUST avoid
  plain print-style application logging.
- **FR-009**: The backend service MUST define a domain error hierarchy and one
  structured error response path at the service boundary.
- **FR-010**: The project MUST include a baseline migration system so future
  persistence changes have a controlled path. The baseline migration MUST enable
  `CREATE EXTENSION IF NOT EXISTS vector` and validation MUST prove pgvector is
  available.
- **FR-011**: The project MUST exclude real secrets, local environment files,
  local virtual environments, caches, local artifacts, and generated data from
  source control.
- **FR-012**: The repository MUST include skeleton documentation for setup,
  architecture, decisions, operations, evaluations, and security.
- **FR-013**: The initial route layer MUST NOT contain persistence calls, cache
  calls, secret-store calls, object-storage calls, model calls, language-model
  calls, or other direct external-system calls.
- **FR-014**: The phase MUST include critical tests covering configuration
  loading, health behavior, structured error behavior, import side effects, and
  route boundary violations.
- **FR-015**: The phase MUST NOT implement GitHub issue fetching, classifiers,
  RAG, authentication, memory, real chatbot behavior, or widget behavior.

### Constitution Alignment *(mandatory)*

- **Phase Scope**: This is `PLAN.md` Phase 1 only. Dataset fetching, model
  training, RAG, auth, memory, chatbot orchestration, Streamlit UI, widget
  implementation, and final CI polish are explicitly out of scope.
- **Architecture Boundaries**: This phase may create and test `app/api`,
  `app/services`, `app/repositories`, `app/domain`, `app/infra`, and
  `app/core` or `app/shared`. Routes remain HTTP-only, services own workflows,
  repositories own persistence, domain models stay distinct from persistence
  models, and infra owns external adapters.
- **Security And Redaction**: This phase handles configuration and local bootstrap
  values only. Real secrets are prohibited. Redaction implementation may be
  skeletal only if clearly marked for later phases, but logs and errors in this
  phase must not expose secret-like configuration values.
- **Observability And Errors**: This phase requires structured logging, request
  identifiers, a domain exception hierarchy, and structured error responses.
  LLM, tool, and RAG spans are not applicable until later phases.
- **Evidence And Evals**: This phase makes no AI, model, RAG, memory, or tracing
  backend decisions requiring eval numbers. It must create documentation
  locations for future measured decisions.
- **Critical Tests**: Critical tests must cover settings loading and failures,
  health checks, one structured error response, import side effects, absence of
  real secrets in repository files, and the rule that routes do not call
  persistence or external systems directly.

### Key Entities *(include if feature involves data)*

- **Configuration Profile**: The set of required and optional local values needed
  to start or validate the foundation, including safe example values only.
- **Health Status**: A report that separates process liveness from shallow
  dependency readiness and identifies unavailable dependencies without exposing
  secrets.
- **Request Context**: Per-request metadata, including request identifier, used
  for correlation across logs and structured errors.
- **Domain Error**: A named application failure that can be mapped to a stable,
  structured user-facing error response.
- **Migration Baseline**: The initial controlled database change point used by
  later phases.
- **Documentation Set**: The initial README, architecture, decisions, runbook,
  evaluations, and security documents that future phases must update.
- **Service Definition**: A local-stack service entry representing one runtime
  component or dependency required by the project foundation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can complete the documented clean-checkout setup and
  local stack validation in under 15 minutes using only example local values.
- **SC-002**: A developer can start the backend foundation and receive successful
  live and ready health responses within 60 seconds on a typical development
  machine after dependencies are available.
- **SC-002a**: `docker compose up` for the default profile starts only the
  backend, migration runner, PostgreSQL/pgvector, Redis, MinIO, and Vault; future
  model-server, chatbot, widget, and host demo services require explicit profile
  selection or remain directory skeletons.
- **SC-002b**: If any default core dependency is unavailable, `/health/ready`
  returns HTTP 503 and includes safe per-check status details; it returns HTTP
  200 only when all default core checks pass.
- **SC-003**: A reviewer can identify every required top-level project area and
  its intended ownership in under 5 minutes using the repository and docs.
- **SC-004**: Automated checks cover configuration loading, health behavior, and
  structured error behavior with no real external credentials required.
- **SC-004a**: Baseline migration validation proves the PostgreSQL `vector`
  extension is enabled and pgvector is available for later phases.
- **SC-005**: Automated or scripted checks can confirm there are no real secrets
  in repository-controlled configuration examples or documentation.
- **SC-006**: A search or architecture test confirms initial routes contain no
  direct persistence, cache, secret-store, object-storage, model, language-model,
  or external-system calls.
- **SC-007**: The foundation contains zero completed future-phase capabilities:
  no issue ingestion, classifier, RAG, auth flow, memory behavior, real chatbot,
  or widget implementation.

## Assumptions

- The project remains a solo bootcamp project optimized for reviewability,
  explicit code, and phase-by-phase delivery.
- Local bootstrap configuration may include fake or development-only values, but
  real credentials are never required for Phase 1.
- Readiness checks in this phase are shallow and bounded; deep dependency checks
  and production monitoring are handled in later phases.
- Documentation skeletons are acceptable in Phase 1 when they clearly identify
  what future phases must record.
- Placeholder runtime services for model server, chatbot, widget, and host demo
  may exist only as startable skeletons; they must not claim real feature
  functionality, and they must not run in the default Phase 1 Compose profile.
