# Implementation Plan: NER and Summarization Tools

**Branch**: `004-ner-summarization` | **Date**: 2026-05-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-ner-summarization/spec.md`

## Summary

Build the Phase 4 issue-analysis tools for Maintainer's Copilot model server.
The work exposes `/ner` and `/summarize` HTTP endpoints with Pydantic request and
response schemas, keeps endpoint handlers thin, implements deterministic
rule-based extraction for code-shaped entities first, places summarization behind
an async timeout-bound adapter with a safe fallback, returns structured tool
errors, and proves that full issue payloads and fake secrets are not logged.

## Technical Context

**Language/Version**: Python 3.11 or newer  
**Primary Dependencies**: FastAPI and Pydantic for model-server endpoints and
schemas; Python `re` and small parsing helpers for rule-based entity extraction;
httpx or an existing async model/LLM client adapter for optional external
summarization; pytest and httpx for service and endpoint tests  
**Storage**: N/A for runtime persistence; no database, Redis, MinIO, or artifact
storage required by this phase  
**Testing**: pytest unit tests for extraction rules, summarization service,
fallback behavior, structured tool errors, redaction/logging expectations, and
schema validation; httpx/ASGI contract tests for `/ner` and `/summarize`  
**Target Platform**: Local developer environment and future CI jobs running the
model server  
**Project Type**: Model-server HTTP tools plus model-server services and infra
adapters  
**Performance Goals**: Rule-based NER runs synchronously but bounded on request
text size; optional external summarization uses an async client with explicit
timeout; no model/client loading at import time or per request  
**Constraints**: Phase 4 only; no chatbot orchestration, RAG retrieval, widget
work, custom NER training, memory persistence, or model-training pipeline;
external summarization credentials are optional and never required for tests;
logs must include request metadata but not full raw issue payloads  
**Scale/Scope**: Two endpoints (`/ner`, `/summarize`), one rule-based entity
extractor, one summarization service, one optional async summarization adapter,
one deterministic fallback, structured errors, and focused tests for supported
entity types and failure paths

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Gate

- **Phase Scope**: PASS. This is `PLAN.md` Phase 4 only. It exposes NER and
  summarization tools and excludes chatbot orchestration, RAG retrieval, widget
  work, auth flows, memory persistence, model training, and custom NER training.
- **Layered Architecture**: PASS. Route handlers stay in `model_server/api` and
  perform request/response mapping only. Extraction and summarization workflows
  live in services. Optional model/LLM clients live in `model_server/infra`.
- **FastAPI Resource Management**: PASS. Optional summarization clients are
  created during model-server lifespan and injected into services. No expensive
  clients, models, or network resources are created at import time or per
  request.
- **Async Safety**: PASS. External summarization uses an async client with an
  explicit timeout. Rule-based NER is bounded by input validation and contains no
  blocking I/O.
- **Secrets And Redaction**: PASS. Provider credentials, if used locally, resolve
  through settings/Vault or test fakes. Tool logs record safe metadata such as
  request ID, text lengths, entity counts, and error codes, not full issue text.
- **Observability And Errors**: PASS. Tool calls return structured errors for
  invalid input, adapter unavailability, timeouts, and unexpected failures. Logs
  retain request correlation without raw payload exposure.
- **AI Evidence And Eval Gates**: PASS. This phase makes no classifier, RAG, or
  model-selection decision. Summarization adapter/fallback choices are documented
  in `research.md` for review.
- **Critical Tests And CI**: PASS. Tests cover supported entity types, response
  schemas, success and failure paths, timeout/fallback behavior, endpoint
  thinness, and no full sensitive payload logging.
- **Simplicity**: PASS. The first version is explainable and rule-based for NER,
  avoids custom NER training, avoids new infrastructure, and uses one optional
  summarization adapter abstraction.

### Post-Design Recheck

- **Phase Scope**: PASS. Generated design artifacts cover only model-server NER
  and summarization tools.
- **Layered Architecture**: PASS. Data model and contracts separate HTTP
  schemas, services, and infra adapters.
- **FastAPI Resource Management**: PASS. The API contract and quickstart require
  lifespan/injected adapter setup and no import-time client construction.
- **Async Safety**: PASS. External summarization is timeout-bound and async;
  deterministic fallback avoids network dependency for tests.
- **Secrets And Redaction**: PASS. Error contracts and quickstart include no
  secrets; tests require fake secret leakage checks.
- **Observability And Errors**: PASS. Contracts define stable error codes and
  request ID propagation.
- **AI Evidence And Eval Gates**: PASS. No model training/eval gate is introduced
  in this phase; adapter choices are documented as implementation constraints.
- **Critical Tests And CI**: PASS. Quickstart and contracts call out extraction,
  summarization, fallback, schema, and logging-redaction checks.
- **Simplicity**: PASS. No complexity exceptions were introduced.

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
└── tasks.md              # Created by /speckit.tasks, not by /speckit.plan
```

### Source Code (repository root)

```text
model_server/
├── api/
│   └── issue_analysis.py
├── domain/
│   └── issue_analysis.py
├── services/
│   ├── entity_extraction_service.py
│   └── summarization_service.py
└── infra/
    └── summarization_client.py

tests/
├── unit/
│   ├── test_entity_extraction_service.py
│   ├── test_summarization_service.py
│   ├── test_issue_analysis_errors.py
│   └── test_issue_analysis_logging.py
└── contract/
    └── test_issue_analysis_endpoints.py

DECISIONS.md              # Add Phase 4 adapter/fallback limitations if needed
```

**Structure Decision**: Keep Phase 4 runtime behavior inside `model_server/`.
Use `model_server/api/issue_analysis.py` for `/ner` and `/summarize` request
mapping, `model_server/domain/issue_analysis.py` for typed Pydantic schemas,
`model_server/services/*` for extraction and summarization behavior, and
`model_server/infra/summarization_client.py` for optional external summarization
providers. Keep tests focused on services, endpoint contracts, structured
errors, and logging redaction.

## Complexity Tracking

No constitution violations or complexity exceptions.
