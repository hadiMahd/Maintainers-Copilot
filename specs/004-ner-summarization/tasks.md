# Tasks: NER and Summarization Tools

**Input**: Design documents from `/specs/004-ner-summarization/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED for critical Phase 4 behavior: typed request and response schemas, supported entity types, combined-length validation, structured timeout and unavailable errors, thin routes, and redacted logging.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Model server**: `model_server/`
- **Shared backend support**: `app/domain`, `app/infra`, `app/core`
- **Project support**: `tests/`, `docs/`, `specs/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the Phase 4 dependencies and file skeletons required by the design.

- [ ] T001 Add Phase 4 runtime dependencies for spaCy and LangSmith-capable summarization in `pyproject.toml`
- [ ] T002 [P] Create Phase 4 model-server module skeletons in `model_server/api/issue_analysis.py`, `model_server/domain/issue_analysis.py`, `model_server/services/ner_service.py`, `model_server/services/summarization_service.py`, `model_server/infra/entity_ruler_pipeline.py`, and `model_server/infra/summarization_adapter.py`
- [ ] T003 [P] Create Phase 4 test file skeletons in `tests/unit/test_entity_ruler_pipeline.py`, `tests/unit/test_ner_service.py`, `tests/unit/test_summarization_service.py`, `tests/unit/test_issue_analysis_redaction.py`, `tests/contract/test_issue_analysis_endpoints.py`, and `tests/integration/test_issue_analysis_lifecycle.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared runtime contracts and lifespan wiring that block both endpoints.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T004 Create shared request, response, span, and tool-error schemas in `model_server/domain/issue_analysis.py`
- [ ] T005 [P] Implement combined-character counting and request normalization helpers in `model_server/domain/issue_analysis.py`
- [ ] T006 [P] Extend runtime settings needed by the summarization adapter in `app/core/config.py`
- [ ] T007 [P] Implement the summarization adapter interface plus fake test adapter seam in `model_server/infra/summarization_adapter.py`
- [ ] T008 [P] Add issue-analysis redaction helpers for bounded logging metadata in `app/infra/redaction.py`
- [ ] T009 Wire issue-analysis lifespan resources and router registration in `model_server/main.py` and `model_server/api/__init__.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Extract Code-Shaped Entities from Issues (Priority: P1) 🎯 MVP

**Goal**: Expose `/ner` with deterministic code-shaped entity extraction and typed entity responses.

**Independent Test**: Submit issue text that covers all supported entity types and verify that `/ner` returns typed entities with deterministic spans and optional confidence fields only when justified.

### Tests for User Story 1 (REQUIRED for critical behavior) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T010 [P] [US1] Add `/ner` contract tests for success and empty-result responses in `tests/contract/test_issue_analysis_endpoints.py`
- [ ] T011 [P] [US1] Add unit tests for spaCy `EntityRuler` pattern coverage, de-duplication, and span mapping in `tests/unit/test_entity_ruler_pipeline.py`
- [ ] T012 [P] [US1] Add unit tests for NER service response shaping in `tests/unit/test_ner_service.py`

### Implementation for User Story 1

- [ ] T013 [P] [US1] Implement the spaCy `EntityRuler` pipeline factory and pattern set in `model_server/infra/entity_ruler_pipeline.py`
- [ ] T014 [US1] Implement deterministic entity extraction, de-duplication, and span mapping in `model_server/services/ner_service.py`
- [ ] T015 [US1] Implement the `/ner` route and typed response mapping in `model_server/api/issue_analysis.py`
- [ ] T016 [US1] Register and invoke the NER service from lifespan-managed app state in `model_server/main.py` and `model_server/api/issue_analysis.py`

**Checkpoint**: At this point, `/ner` should be fully functional and testable independently.

---

## Phase 4: User Story 2 - Summarize Long Issue Threads (Priority: P2)

**Goal**: Expose `/summarize` with Azure OpenAI via LangChain, using a fake adapter in tests and typed summary responses on success.

**Independent Test**: Submit a representative long issue thread and verify that `/summarize` returns `summary`, `key_facts`, `unresolved_questions`, and optional `suggested_next_step` without requiring real Azure credentials in automated tests.

### Tests for User Story 2 (REQUIRED for critical behavior) ⚠️

- [ ] T017 [P] [US2] Add `/summarize` contract tests for successful summary responses in `tests/contract/test_issue_analysis_endpoints.py`
- [ ] T018 [P] [US2] Add unit tests for summarization service success-path shaping with the fake adapter in `tests/unit/test_summarization_service.py`
- [ ] T019 [P] [US2] Add integration tests for summarization resource wiring in `tests/integration/test_issue_analysis_lifecycle.py`

### Implementation for User Story 2

- [ ] T020 [P] [US2] Implement Azure OpenAI LangChain adapter creation and LangSmith-aware configuration in `model_server/infra/summarization_adapter.py`
- [ ] T021 [US2] Implement summarization workflow, response shaping, and next-step handling in `model_server/services/summarization_service.py`
- [ ] T022 [US2] Implement the `/summarize` route and typed success response mapping in `model_server/api/issue_analysis.py`
- [ ] T023 [US2] Attach summarization adapter readiness to model-server lifespan state in `model_server/main.py`

**Checkpoint**: At this point, `/summarize` should succeed independently with the fake adapter and structured typed responses.

---

## Phase 5: User Story 3 - Handle Tool Failures Safely (Priority: P3)

**Goal**: Return structured validation, timeout, and unavailable-tool errors without crashing the model server or logging full payloads.

**Independent Test**: Trigger invalid input, oversized input, adapter unavailability, and timeout conditions, then verify structured `422`/`503` responses, healthy process state, thin routes, and redacted logs.

### Tests for User Story 3 (REQUIRED for critical behavior) ⚠️

- [ ] T024 [P] [US3] Add contract tests for invalid input, oversized payloads, and structured summarizer failure responses in `tests/contract/test_issue_analysis_endpoints.py`
- [ ] T025 [P] [US3] Add redaction leak tests for issue-analysis logs and fake secrets in `tests/unit/test_issue_analysis_redaction.py`
- [ ] T026 [P] [US3] Add route-boundary coverage for issue-analysis handlers in `tests/test_route_boundaries.py`
- [ ] T027 [P] [US3] Add lifecycle tests proving tool failures do not crash the model server in `tests/integration/test_issue_analysis_lifecycle.py`

### Implementation for User Story 3

- [ ] T028 [US3] Implement combined-length validation and structured input-error mapping in `model_server/domain/issue_analysis.py` and `model_server/api/issue_analysis.py`
- [ ] T029 [US3] Implement summarizer timeout and unavailable-adapter exception mapping in `model_server/services/summarization_service.py`
- [ ] T030 [US3] Implement payload-safe logging and redacted tool metadata emission in `model_server/services/ner_service.py`, `model_server/services/summarization_service.py`, and `app/infra/redaction.py`
- [ ] T031 [US3] Keep issue-analysis routes thin by delegating adapter calls fully to services in `model_server/api/issue_analysis.py`

**Checkpoint**: All Phase 4 user stories should now be independently functional and safe under expected failure modes.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finish docs and validation that affect multiple user stories.

- [ ] T032 [P] Update operational and AI-design notes for Phase 4 in `docs/decisions.md` and `docs/security.md`
- [ ] T033 Align the quickstart commands and example payloads with the implemented routes in `specs/004-ner-summarization/quickstart.md`
- [ ] T034 Run the Phase 4 quickstart validation flow and record any command corrections in `specs/004-ner-summarization/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: Depend on Foundational completion
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - no dependency on other stories
- **User Story 2 (P2)**: Can start after Foundational - reuses shared schemas and lifespan wiring but remains independently testable with a fake adapter
- **User Story 3 (P3)**: Can start after Foundational and is completed after US1/US2 route and service behavior exist

### Within Each User Story

- Required tests MUST be written and fail before implementation
- Infra builders before services
- Services before routes
- Validation, error mapping, and logging before final completion

### Parallel Opportunities

- Setup: `T002`, `T003`
- Foundational: `T005`, `T006`, `T007`, `T008`
- US1: `T010`, `T011`, `T012` then `T013`
- US2: `T017`, `T018`, `T019` then `T020`
- US3: `T024`, `T025`, `T026`, `T027`

---

## Parallel Example: User Story 1

```bash
# Launch US1 tests together:
Task: "Add /ner contract tests in tests/contract/test_issue_analysis_endpoints.py"
Task: "Add EntityRuler coverage tests in tests/unit/test_entity_ruler_pipeline.py"
Task: "Add NER service tests in tests/unit/test_ner_service.py"

# After tests exist, launch independent infra work:
Task: "Implement the EntityRuler pipeline factory in model_server/infra/entity_ruler_pipeline.py"
```

---

## Parallel Example: User Story 2

```bash
# Launch US2 tests together:
Task: "Add /summarize contract tests in tests/contract/test_issue_analysis_endpoints.py"
Task: "Add summarization service tests in tests/unit/test_summarization_service.py"
Task: "Add summarization lifecycle tests in tests/integration/test_issue_analysis_lifecycle.py"

# Then implement the adapter seam independently:
Task: "Implement Azure OpenAI LangChain adapter creation in model_server/infra/summarization_adapter.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Stop and validate `/ner` independently

### Incremental Delivery

1. Finish Setup + Foundational
2. Deliver `/ner` as the first usable tool
3. Add `/summarize` with the fake adapter test path
4. Add failure-safety and redaction hardening
5. Finish docs and quickstart validation

### Suggested MVP Scope

Implement through **User Story 1** first. It gives a fully testable tool and
establishes the request/response and lifespan patterns needed by the rest of the phase.
