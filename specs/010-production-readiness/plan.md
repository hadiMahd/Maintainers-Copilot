# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]  
**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]  
**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]  
**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]  
**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]
**Project Type**: [e.g., library/cli/web-service/mobile-app/compiler/desktop-app or NEEDS CLARIFICATION]  
**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]  
**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]  
**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Fill this section with a pass/fail assessment against
`.specify/memory/constitution.md`. Any failing gate MUST be fixed before
implementation or recorded in Complexity Tracking with a concrete justification.

- **Phase Scope**: Confirms the plan implements only the current `PLAN.md` phase,
  keeps future-phase behavior absent or clearly stubbed, and does not add
  speculative product features.
- **Layered Architecture**: Confirms API routes stay HTTP-only; services own
  workflows, transaction boundaries, cache invalidation, and memory invalidation;
  repositories own persistence only; domain models stay distinct from ORM models;
  infra owns external adapters.
- **FastAPI Resource Management**: Confirms app factory, lifespan, and dependency
  injection own settings, sessions, repositories, services, current user, Redis,
  Vault, LLM clients, model clients, and request context. Confirms no expensive
  resources are created at import time or per request.
- **Async Safety**: Confirms async request paths avoid blocking clients, sync
  database calls, sync LLM calls, `time.sleep`, and large sync file reads.
  Confirms async clients and explicit timeouts are planned.
- **Secrets And Redaction**: Confirms real secrets are excluded, Vault or test
  fakes resolve sensitive values, and redaction runs before logs, traces, audit
  metadata, and memory writes.
- **Observability And Errors**: Confirms structured logs, request IDs, trace IDs,
  LLM/tool/RAG spans, domain exceptions, and structured HTTP error mapping.
- **AI Evidence And Eval Gates**: For AI, RAG, memory, or model phases, confirms
  metrics, golden sets, non-zero thresholds, model cards, artifact hashes, and
  `DECISIONS.md` updates are planned.
- **Critical Tests And CI**: Confirms tests cover critical behavior and release
  gates for the phase, including redaction leaks and eval regressions where
  applicable.
- **Simplicity**: Confirms the design uses one tool-calling LLM for chatbot work,
  avoids multi-agent systems, avoids unneeded infrastructure, and favors explicit
  code over clever abstractions.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
app/
├── api/                 # HTTP routing, dependencies, response mapping only
├── services/            # Business workflows and transaction/cache ownership
├── repositories/        # SQL and persistence only
├── domain/              # Pydantic domain models distinct from ORM models
├── infra/               # Vault, MinIO, Redis, LLM, model, tracing, redaction
└── core/ or shared/     # Cross-cutting app concerns only

model_server/
chatbot/
widget/
demo/host/
scripts/
tests/
docs/
prompts/
evals/
data/raw/
data/processed/
artifacts/
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
