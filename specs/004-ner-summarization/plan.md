# Implementation Plan: NER and Summarization Tools

**Branch**: `004-ner-summarization` | **Date**: 2026-05-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-ner-summarization/spec.md`

## Summary

Build the Phase 4 issue-analysis tools in `model_server`: a deterministic NER
endpoint backed by a spaCy `EntityRuler` pipeline for code-shaped entities, and
an Azure OpenAI summarization endpoint backed by LangChain
`AzureChatOpenAI` with LangSmith tracing when configured. Both endpoints use
typed request/response models, enforce an 8,000-character combined input limit,
return structured tool errors on invalid input or provider failure, avoid
logging full issue payloads, and keep adapter logic in infra while routes stay
thin.

## Technical Context

**Language/Version**: Python 3.11 or newer  
**Primary Dependencies**: FastAPI, pydantic, spaCy (`EntityRuler`), LangChain
Core, `langchain-openai` (`AzureChatOpenAI`), existing Vault bootstrap
settings, existing redaction helper, structlog or existing structured logging,
pytest, pytest-asyncio, httpx  
**Storage**: N/A for endpoint payloads; runtime secrets resolve from Vault;
LangSmith traces are optional external telemetry when a tracing key is present  
**Testing**: pytest unit tests for request validation, entity extraction,
summarization response shaping, adapter timeout/unavailable behavior, and safe
logging; contract tests for `/ner` and `/summarize`; integration tests for
model-server lifespan wiring and failure isolation  
**Target Platform**: Local Linux/container development environment, CI, and the
Phase 4 `model_server` runtime  
**Project Type**: FastAPI model-server feature with deterministic local NER and
provider-backed summarization  
**Performance Goals**: In-process NER remains synchronous-but-bounded and
returns results for representative 8,000-character inputs without external
calls; summarization calls are hard-bounded by a 15-second timeout and never
block beyond that timeout window  
**Constraints**: Combined title + body + comments length must not exceed 8,000
characters; no fallback summary content when Azure OpenAI is unavailable or
times out; no full issue payload logging; no chatbot orchestration, RAG,
memory, widget, auth, or custom NER training in this phase; automated tests
must run with a fake LangChain adapter and no real Azure credentials  
**Scale/Scope**: Two endpoints, ten supported entity types, one deterministic
spaCy pipeline, one Azure summarization adapter, one fake summarization adapter
for tests, and one shared structured error contract

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Gate

- **Phase Scope**: PASS. This plan implements only Phase 4 issue-analysis
  tools. Chatbot orchestration, RAG retrieval, memory, auth, widget, and model
  training stay out of scope.
- **Layered Architecture**: PASS. Routes stay request/response only. NER and
  summarization behavior lives in `model_server/services/`. spaCy and LangChain
  adapters live in `model_server/infra/`. Shared redaction remains in
  `app/infra/`.
- **FastAPI Resource Management**: PASS. The spaCy pipeline and summarization
  adapter are created during model-server lifespan and attached to app state.
  No expensive resources are created at import time or per request.
- **Async Safety**: PASS. The Azure summarization path uses an async LangChain
  adapter with an explicit 15-second timeout. NER does not perform network I/O.
  CPU-heavy model training remains absent.
- **Secrets And Redaction**: PASS. Azure and LangSmith configuration continue to
  resolve through Vault bootstrap settings. Logs and traces use redacted,
  bounded metadata rather than raw title/body/comments.
- **Observability And Errors**: PASS. Request IDs propagate through both
  endpoints. Summarization runs emit traceable adapter spans when LangSmith is
  configured. Failures map to structured tool errors.
- **AI Evidence And Eval Gates**: PASS. This phase does not introduce a new
  model-selection gate. It documents adapter choices, timeout behavior, and
  error policy instead of new eval thresholds.
- **Critical Tests And CI**: PASS. Planned tests cover typed schemas, supported
  entity types, timeout/unavailable paths, and redaction behavior.
- **Simplicity**: PASS. One deterministic local NER path and one summarization
  adapter path are enough for the phase. No extra infrastructure or multi-agent
  behavior is introduced.

## Project Structure

### Documentation (this feature)

```text
specs/004-ner-summarization/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── issue-analysis.openapi.yaml
└── tasks.md
```

### Source Code (repository root)

```text
model_server/
├── api/
│   └── issue_analysis.py
├── domain/
│   └── issue_analysis.py
├── services/
│   ├── ner_service.py
│   └── summarization_service.py
├── infra/
│   ├── entity_ruler_pipeline.py
│   └── summarization_adapter.py
└── main.py

app/
├── domain/
│   └── errors.py
└── infra/
    └── redaction.py

tests/
├── unit/
│   ├── test_entity_ruler_pipeline.py
│   ├── test_ner_service.py
│   ├── test_summarization_service.py
│   └── test_issue_analysis_redaction.py
├── contract/
│   └── test_issue_analysis_endpoints.py
└── integration/
    └── test_issue_analysis_lifecycle.py
```

**Structure Decision**: Keep all Phase 4 runtime behavior inside `model_server`,
reusing only shared cross-cutting helpers such as domain errors and redaction
from `app/`. This avoids smearing model-server tool behavior across the backend
API while preserving the repo’s existing layered boundaries.

## Complexity Tracking

No constitution violations or complexity exceptions are planned.

## Post-Design Constitution Check

- **Phase Scope**: PASS. Design artifacts cover only `/ner` and `/summarize`
  plus their local adapters, tests, and contracts.
- **Layered Architecture**: PASS. Contracts and data model keep route schemas,
  services, and infra adapters separate.
- **FastAPI Resource Management**: PASS. Lifespan owns the spaCy pipeline and
  summarization adapter; routes depend on app state and services only.
- **Async Safety**: PASS. The only external call is the async Azure OpenAI
  summarization path with an explicit timeout. No sync HTTP clients are planned
  in async routes.
- **Secrets And Redaction**: PASS. Real secrets stay in Vault. Redaction rules
  remain mandatory before logs or trace metadata.
- **Observability And Errors**: PASS. Structured tool errors and request-aware
  logging remain part of the contract. LangSmith tracing is optional but
  explicit when configured.
- **AI Evidence And Eval Gates**: PASS. This phase does not claim new model
  performance numbers; it documents provider and timeout choices instead.
- **Critical Tests And CI**: PASS. Unit, contract, and integration tests cover
  the phase-critical behavior and safety boundaries.
- **Simplicity**: PASS. The plan stays with one deterministic NER strategy and
  one provider-backed summarization strategy, with a fake adapter for tests
  instead of a second production summarizer.
