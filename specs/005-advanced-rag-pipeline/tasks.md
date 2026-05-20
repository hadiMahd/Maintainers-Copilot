# Tasks: Advanced RAG Pipeline

**Input**: Design documents from `/specs/005-advanced-rag-pipeline/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED for critical Phase 5 behavior: parent-document chunking with `parent_id`, classifier/RAG data-split isolation, duplicate embedding avoidance, retrieval result schemas, metadata filtering, sparse/dense/hybrid ranking, query transformation toggling, reranking impact, grounded-answer insufficiency behavior, frozen `judge_id` report metadata, snapshot redaction with 50-conversation retention, and baseline-vs-advanced eval gate enforcement.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `app/core`, `app/domain`, `app/services`, `app/repositories`, `app/infra`
- **Project support**: `scripts/`, `tests/`, `docs/`, `evals/`, `artifacts/`, `data/processed/`, `migrations/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the Phase 5 dependencies and create the file skeletons required by the design.

- [x] T001 Add Phase 5 runtime dependencies for pgvector, sentence-transformers, cross-encoder reranking, and optional provider adapters in `pyproject.toml`
- [x] T002 [P] Create Phase 5 service, repository, infra, and script skeletons in `app/domain/rag.py`, `app/services/rag_ingestion_service.py`, `app/services/rag_index_service.py`, `app/services/rag_retrieval_service.py`, `app/services/rag_generation_service.py`, `app/services/rag_evaluation_service.py`, `app/services/rag_snapshot_service.py`, `app/repositories/rag_chunk_repository.py`, `app/repositories/rag_embedding_repository.py`, `app/repositories/rag_snapshot_repository.py`, `app/infra/embedding_client.py`, `app/infra/reranker_client.py`, `app/infra/rag_generation_client.py`, `app/infra/rag_judge_client.py`, `scripts/ingest_docs.py`, `scripts/ingest_resolved_issues.py`, `scripts/build_rag_index.py`, and `scripts/evaluate_rag.py`
- [x] T003 [P] Create Phase 5 test file skeletons in `tests/contract/test_rag_commands.py`, `tests/contract/test_rag_service_contract.py`, `tests/unit/test_rag_chunking.py`, `tests/unit/test_rag_generation_service.py`, `tests/unit/test_rag_metadata_filtering.py`, `tests/unit/test_rag_retrieval_schema.py`, `tests/unit/test_rag_hybrid_scoring.py`, `tests/unit/test_rag_query_transformation.py`, `tests/unit/test_rag_reranking.py`, `tests/unit/test_rag_eval_metrics.py`, `tests/unit/test_rag_observability.py`, `tests/unit/test_rag_provider_resolution.py`, `tests/unit/test_rag_redaction.py`, `tests/unit/test_rag_snapshot_service.py`, `tests/integration/test_rag_grounded_answers.py`, `tests/integration/test_rag_index_scripts.py`, and `tests/integration/test_rag_pgvector_retrieval.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared schemas, storage, settings, and adapter seams that block every RAG workflow.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T004 Create typed RAG entities, queries, retrieval results, grounded answers, eval runs, eval reports, and snapshot schemas in `app/domain/rag.py`
- [x] T005 [P] Extend typed RAG settings for embedding candidates, hybrid weights, reranker controls, generation/judge timeouts, snapshot retention, eval thresholds, and Vault-backed provider resolution in `app/core/config.py`
- [x] T006 [P] Add RAG redaction helpers for source payloads, prompts, retrieved previews, trace attributes, snapshot rows, and eval reports in `app/infra/redaction.py`
- [x] T007 [P] Add Phase 5 Alembic tables and indexes for RAG sources, chunks, embeddings, sparse search fields, and retrieved-chunk snapshots in `migrations/versions/0002_phase5_rag_tables.py`
- [x] T008 [P] Implement async repository scaffolding for chunks, embeddings, and snapshots in `app/repositories/rag_chunk_repository.py`, `app/repositories/rag_embedding_repository.py`, and `app/repositories/rag_snapshot_repository.py`
- [x] T009 [P] Add unit tests for Vault-backed provider resolution, fake-provider fallback, and no-secret config handling in `tests/unit/test_rag_provider_resolution.py`
- [x] T010 [P] Add unit tests for retrieval, generation, judge, and eval trace emission with safe redacted attributes in `tests/unit/test_rag_observability.py`
- [x] T011 [P] Implement provider/client seams for local and Azure embeddings, reranking, grounded generation, and frozen judging with Vault-backed secret resolution and trace hooks in `app/infra/embedding_client.py`, `app/infra/reranker_client.py`, `app/infra/rag_generation_client.py`, and `app/infra/rag_judge_client.py`
- [x] T012 Wire shared RAG service scaffolding, structured domain errors, request_id/trace_id correlation, and trace emission helpers in `app/services/rag_ingestion_service.py`, `app/services/rag_index_service.py`, `app/services/rag_retrieval_service.py`, `app/services/rag_generation_service.py`, `app/services/rag_evaluation_service.py`, `app/services/rag_snapshot_service.py`, and `app/domain/rag.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Answer Maintainer Questions With Grounded Evidence (Priority: P1) 🎯 MVP

**Goal**: Retrieve relevant evidence and produce grounded answers that cite supporting chunks or explicitly report insufficient evidence.

**Independent Test**: Use fixture-backed chunks and fake generation adapters to ask representative maintainer questions and verify retrieved evidence, supporting chunk references, and insufficient-evidence behavior without requiring the full ingestion/index pipeline.

### Tests for User Story 1 (REQUIRED for critical behavior) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T013 [P] [US1] Add service-contract tests for retrieval result schemas, supporting chunk references, and insufficient-evidence responses in `tests/contract/test_rag_service_contract.py`
- [x] T014 [P] [US1] Add unit tests for grounded-answer shaping, evidence-only generation, and redacted prompt handling in `tests/unit/test_rag_generation_service.py` and `tests/unit/test_rag_redaction.py`
- [x] T015 [P] [US1] Add integration tests for question-to-answer flow using fixture-backed retrieval results and fake generation adapters in `tests/integration/test_rag_grounded_answers.py`

### Implementation for User Story 1

- [x] T016 [P] [US1] Implement retrieval-result shaping, metadata filter application, empty-result explanations, and retrieval span emission in `app/services/rag_retrieval_service.py` and `app/repositories/rag_chunk_repository.py`
- [x] T017 [P] [US1] Implement grounded-generation adapter behavior, evidence citation formatting, insufficiency detection, and provider trace hooks in `app/infra/rag_generation_client.py` and `app/services/rag_generation_service.py`
- [x] T018 [US1] Implement the grounded-answer workflow that composes retrieval and generation with structured domain errors in `app/services/rag_retrieval_service.py`, `app/services/rag_generation_service.py`, and `app/domain/rag.py`
- [x] T019 [US1] Add payload-safe logging, run/request correlation, trace-safe attributes, and safe failure mapping for grounded-answer operations in `app/services/rag_retrieval_service.py`, `app/services/rag_generation_service.py`, and `app/infra/redaction.py`

**Checkpoint**: At this point, grounded question answering should be independently testable with fixture corpora and fake providers.

---

## Phase 4: User Story 2 - Prove The Advanced Pipeline Beats The Naive Baseline (Priority: P2)

**Goal**: Produce a reviewable eval report that compares naive and advanced RAG modes on the same 25-example golden set and records the frozen CI judge identity.

**Independent Test**: Run the evaluation flow against a fixture-backed corpus and fake generation/judge adapters, then verify that the report includes all required metrics, `judge_id`, disagreement notes, and threshold-gate behavior.

### Tests for User Story 2 (REQUIRED for critical behavior) ⚠️

- [x] T020 [P] [US2] Add command-contract tests for `scripts/evaluate_rag.py` report shape, threshold failures, safe stderr behavior, and `judge_id` recording in `tests/contract/test_rag_commands.py`
- [x] T021 [P] [US2] Add unit tests for token-overlap judging, hit@5 and MRR@10 calculation, latency aggregation, report schema validation, and two-candidate embedding comparison outputs in `tests/unit/test_rag_eval_metrics.py`
- [x] T022 [P] [US2] Add integration tests for baseline-vs-advanced evaluation using fixture corpora and fake providers, including five hand-labeled disagreement examples and both embedding candidates in `tests/integration/test_rag_grounded_answers.py`

### Implementation for User Story 2

- [x] T023 [P] [US2] Create the 25-example golden set, five hand-labeled disagreement examples, and Phase 5 eval thresholds in `evals/rag_golden_set.jsonl` and `evals/eval_thresholds.yaml`
- [x] T024 [P] [US2] Implement the frozen token-overlap judge, optional non-CI judge plumbing, and judge trace hooks in `app/infra/rag_judge_client.py`
- [x] T025 [US2] Implement baseline/advanced metric aggregation, latency measurement, disagreement-note capture, two-candidate embedding comparison reporting, and report shaping in `app/services/rag_evaluation_service.py`
- [x] T026 [US2] Implement `scripts/evaluate_rag.py` to run both modes, persist `evals/rag_eval_report.json`, record `judge_id`, validate both embedding candidates in comparison outputs, and fail when advanced hit@5 or MRR@10 does not exceed baseline outside exploratory mode

**Checkpoint**: At this point, the evaluation flow should produce a schema-valid comparison report with deterministic CI judge metadata.

---

## Phase 5: User Story 3 - Build A Repeatable Knowledge Corpus (Priority: P3)

**Goal**: Repeatedly ingest docs and held-out maintainer-answer issues, chunk them with `parent_id` metadata, and generate deduplicated embeddings safely.

**Independent Test**: Run the ingestion and indexing scripts twice on the same fixture inputs and verify stable hashes, stable chunk IDs, no classifier-data leakage, and no duplicate embeddings for unchanged content.

### Tests for User Story 3 (REQUIRED for critical behavior) ⚠️

- [x] T027 [P] [US3] Add unit tests for parent-document chunking, stable child IDs, source metadata completeness, and classifier-data leakage rejection in `tests/unit/test_rag_chunking.py`
- [x] T028 [P] [US3] Add integration tests for repeatable doc/issue ingestion and duplicate embedding skipping in `tests/integration/test_rag_index_scripts.py`

### Implementation for User Story 3

- [x] T029 [P] [US3] Implement normalized doc and issue source parsing plus parent-document child chunk building in `app/services/rag_ingestion_service.py` and `app/domain/rag.py`
- [x] T030 [P] [US3] Implement the documentation and held-out issue ingestion commands in `scripts/ingest_docs.py` and `scripts/ingest_resolved_issues.py`
- [x] T031 [P] [US3] Implement chunk persistence, sparse-search text preparation, and duplicate embedding checks by `content_hash` plus embedding model in `app/repositories/rag_chunk_repository.py`, `app/repositories/rag_embedding_repository.py`, and `app/services/rag_index_service.py`
- [x] T032 [US3] Implement local `all-MiniLM-L6-v2` and optional Azure `text-embedding-3-small` embedding clients plus index-building orchestration in `app/infra/embedding_client.py` and `scripts/build_rag_index.py`
- [x] T033 [US3] Persist repeatable corpus artifacts and embedding comparison outputs in `data/processed/rag_doc_sources.jsonl`, `data/processed/rag_issue_answer_sources.jsonl`, `data/processed/rag_chunks.jsonl`, `artifacts/rag/embedding_comparison.json`, and `app/services/rag_index_service.py`

**Checkpoint**: At this point, the corpus and embedding pipeline should rerun safely with stable identifiers and no duplicate embeddings.

---

## Phase 6: User Story 4 - Compare Retrieval Controls And Ranking Stages (Priority: P4)

**Goal**: Make sparse, dense, hybrid, query transformation, metadata filtering, reranking, and snapshot retention observable and measurable.

**Independent Test**: Run retrieval with sparse/dense/hybrid modes, query transformation on and off, metadata filters, reranking enabled, and snapshot storage enabled; then verify scored outputs, deterministic ranking behavior, reranking impact, redacted snapshots, and bounded 50-conversation retention.

### Tests for User Story 4 (REQUIRED for critical behavior) ⚠️

- [ ] T034 [P] [US4] Add unit tests for sparse/dense score normalization and hybrid weighting behavior in `tests/unit/test_rag_hybrid_scoring.py`
- [ ] T035 [P] [US4] Add unit tests for metadata filtering and query transformation toggling in `tests/unit/test_rag_metadata_filtering.py` and `tests/unit/test_rag_query_transformation.py`
- [ ] T036 [P] [US4] Add unit tests for reranking impact, deterministic tie handling, snapshot redaction, conversation/message/trace metadata association, and 50-conversation retention in `tests/unit/test_rag_reranking.py`, `tests/unit/test_rag_snapshot_service.py`, and `tests/unit/test_rag_redaction.py`
- [ ] T037 [P] [US4] Add integration tests for pgvector-backed retrieval, empty filtered result sets, and reranking-driven rank changes in `tests/integration/test_rag_pgvector_retrieval.py`

### Implementation for User Story 4

- [ ] T038 [P] [US4] Implement PostgreSQL full-text sparse retrieval, dense retrieval, and weighted hybrid ranking in `app/repositories/rag_chunk_repository.py` and `app/services/rag_retrieval_service.py`
- [ ] T039 [P] [US4] Implement query transformation toggling and safe empty-result explanations in `app/services/rag_retrieval_service.py` and `app/infra/rag_generation_client.py`
- [ ] T040 [P] [US4] Implement top-k cross-encoder reranking and deterministic final ordering in `app/infra/reranker_client.py` and `app/services/rag_retrieval_service.py`
- [ ] T041 [US4] Implement redacted retrieved-chunk snapshot storage with conversation/message/trace metadata and 50-conversation retention in `app/services/rag_snapshot_service.py` and `app/repositories/rag_snapshot_repository.py`
- [ ] T042 [US4] Wire retrieval-mode metadata, reranking impact, query transformation mode, trace-safe previews, and eval trace metadata into `app/services/rag_evaluation_service.py` and `scripts/evaluate_rag.py`

**Checkpoint**: All retrieval controls and ranking stages should now be independently testable and measurable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Finish reviewer docs, operational notes, and validation that span multiple user stories.

- [ ] T043 [P] Update Phase 5 decision and evaluation documentation in `DECISIONS.md` and `docs/evals.md`
- [ ] T044 [P] Update RAG architecture, security, and operator guidance in `docs/architecture.md`, `docs/security.md`, and `docs/runbook.md`
- [ ] T045 Validate Phase 5 quickstart commands, artifact paths, and report expectations in `specs/005-advanced-rag-pipeline/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: Depend on Foundational completion
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - independent validation uses fixture-backed chunks and fake generation adapters
- **User Story 2 (P2)**: Can start after Foundational - independent validation uses fixture corpora and fake providers, but final end-to-end report quality benefits from US3 and US4 being complete
- **User Story 3 (P3)**: Can start after Foundational - provides the repeatable real corpus and indexing path used by final US1, US2, and US4 validation
- **User Story 4 (P4)**: Can start after Foundational - independent validation uses repository-backed fixtures, and its outputs feed the final advanced evaluation path

### Within Each User Story

- Required tests MUST be written and fail before implementation
- Domain and repository contracts before orchestration
- Infra adapters before service orchestration
- Scripts after underlying services and repositories exist
- Report, redaction, and threshold behavior before final completion

### Parallel Opportunities

- Setup: `T002`, `T003`
- Foundational: `T005`, `T006`, `T007`, `T008`, `T009`, `T010`
- US1: `T013`, `T014`, `T015` then `T016`, `T017`
- US2: `T020`, `T021`, `T022` then `T023`, `T024`
- US3: `T027`, `T028` then `T029`, `T030`, `T031`
- US4: `T034`, `T035`, `T036`, `T037` then `T038`, `T039`, `T040`

---

## Parallel Example: User Story 1

```bash
# Launch US1 tests together:
Task: "Add retrieval/generation service contract tests in tests/contract/test_rag_service_contract.py"
Task: "Add grounded-generation and redaction unit tests in tests/unit/test_rag_generation_service.py and tests/unit/test_rag_redaction.py"
Task: "Add fixture-backed grounded-answer integration tests in tests/integration/test_rag_grounded_answers.py"

# Then implement the independent service seams:
Task: "Implement retrieval-result shaping in app/services/rag_retrieval_service.py and app/repositories/rag_chunk_repository.py"
Task: "Implement grounded-generation adapter behavior in app/infra/rag_generation_client.py and app/services/rag_generation_service.py"
```

---

## Parallel Example: User Story 2

```bash
# Launch US2 tests together:
Task: "Add evaluate_rag command contract tests in tests/contract/test_rag_commands.py"
Task: "Add eval metric and judge unit tests in tests/unit/test_rag_eval_metrics.py"
Task: "Add baseline-vs-advanced integration tests in tests/integration/test_rag_grounded_answers.py"

# Then implement eval fixtures and judging in parallel:
Task: "Create the golden set and thresholds in evals/rag_golden_set.jsonl and evals/eval_thresholds.yaml"
Task: "Implement the frozen judge in app/infra/rag_judge_client.py"
```

---

## Parallel Example: User Story 3

```bash
# Launch US3 tests together:
Task: "Add parent-document chunking tests in tests/unit/test_rag_chunking.py"
Task: "Add repeatable ingestion/index script tests in tests/integration/test_rag_index_scripts.py"

# Then implement ingestion/index pieces in parallel:
Task: "Implement doc and issue parsing in app/services/rag_ingestion_service.py and app/domain/rag.py"
Task: "Implement ingestion commands in scripts/ingest_docs.py and scripts/ingest_resolved_issues.py"
Task: "Implement duplicate embedding checks in app/repositories/rag_embedding_repository.py and app/services/rag_index_service.py"
```

---

## Parallel Example: User Story 4

```bash
# Launch US4 tests together:
Task: "Add hybrid scoring tests in tests/unit/test_rag_hybrid_scoring.py"
Task: "Add metadata filtering and query transformation tests in tests/unit/test_rag_metadata_filtering.py and tests/unit/test_rag_query_transformation.py"
Task: "Add reranking, snapshot retention, and redaction tests in tests/unit/test_rag_reranking.py, tests/unit/test_rag_snapshot_service.py, and tests/unit/test_rag_redaction.py"
Task: "Add pgvector retrieval integration tests in tests/integration/test_rag_pgvector_retrieval.py"

# Then implement the retrieval controls in parallel:
Task: "Implement weighted hybrid ranking in app/repositories/rag_chunk_repository.py and app/services/rag_retrieval_service.py"
Task: "Implement reranker integration in app/infra/reranker_client.py and app/services/rag_retrieval_service.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Stop and validate grounded question answering with fixture-backed retrieval

### Incremental Delivery

1. Finish Setup + Foundational
2. Deliver grounded question answering with fake providers (US1)
3. Add deterministic evaluation and CI judge reporting (US2)
4. Add repeatable real corpus and index-building pipeline (US3)
5. Add advanced retrieval controls, reranking, and snapshot retention (US4)
6. Finish docs and quickstart validation

### Suggested MVP Scope

Implement through **User Story 1** first. It establishes the core retrieval,
grounded-generation, redaction, and domain-error patterns while staying
independently testable with fixture-backed corpora.
