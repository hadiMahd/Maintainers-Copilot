# Implementation Plan: Advanced RAG Pipeline

**Branch**: `005-advanced-rag-pipeline` | **Date**: 2026-05-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-advanced-rag-pipeline/spec.md`

## Summary

Build the Phase 5 advanced RAG pipeline for Maintainer's Copilot. The work
ingests project documentation and held-out resolved issues with maintainer
answers, creates structure-aware chunks with metadata, stores chunks and
embeddings in PostgreSQL with pgvector, implements sparse/dense/hybrid retrieval,
adds query transformation, metadata filtering, small cross-encoder reranking, and
grounded answer generation, then evaluates the advanced pipeline against a naive
fixed-size chunking plus pure dense retrieval baseline on a 25-example RAG golden
set using a frozen local/mockable judge for CI faithfulness and answer relevancy.
The RAG service also exposes redacted retrieved-chunk snapshot storage for the
last N conversations when later chat phases call it. Long-running ingestion,
embedding, and evaluation run through scripts, not API request paths.

## Technical Context

**Language/Version**: Python 3.11 or newer  
**Primary Dependencies**: SQLAlchemy async and asyncpg for PostgreSQL access;
PostgreSQL 16 with pgvector for vector storage and similarity search;
PostgreSQL full-text search for the first sparse retrieval path; Alembic for RAG
tables/indexes; small sentence-transformers embedding candidates for comparison;
a small cross-encoder reranker; pytest for chunking, filtering, retrieval schema,
deduplication, and eval-report tests; a frozen local/mockable judge for required
CI generation metrics; optional async LLM/model client adapters with explicit
timeouts for query transformation, grounded generation, optional RAGAS-style
metrics, and non-CI judging  
**Storage**: PostgreSQL tables for RAG sources, chunks, embeddings, sparse search
fields, eval run metadata, and redacted retrieved-chunk snapshots; JSONL/JSON
artifacts under `data/processed/`, `evals/`, and `artifacts/rag/`;
`DECISIONS.md` for selected RAG choices  
**Testing**: pytest unit tests for chunking, metadata filtering, score merging,
query transformation toggling, reranker impact, grounded answer behavior,
embedding deduplication, eval metric calculation, report schema, and redaction;
integration tests for repeatable scripts and pgvector-backed retrieval where the
local database is available; snapshot tests for redaction and last-N retention  
**Target Platform**: Local developer environment, Docker Compose PostgreSQL with
pgvector, and future CI jobs  
**Project Type**: Script-driven RAG ingestion/indexing/evaluation plus backend
RAG services and repositories  
**Performance Goals**: Evaluation records retrieval latency and generation
latency for baseline and advanced modes; API-facing retrieval/generation paths
use async database/model access with explicit timeouts; ingestion and embedding
never run in request paths  
**Constraints**: Phase 5 only; no UI work, full chatbot orchestration, auth
flows, memory persistence, or widget behavior; no Qdrant unless already selected
(it has not been selected); no real secrets in scripts, fixtures, reports, or
logs; RAG eval must beat the naive baseline on hit@5 and MRR@10 before the phase
is considered complete  
**Scale/Scope**: One documentation corpus, one held-out issue-answer corpus, one
naive baseline, at least two embedding model candidates, pgvector vector
storage, PostgreSQL full-text sparse retrieval, dense retrieval, hybrid retrieval
with tuned weighting, query transformation toggle, metadata filters, top-k
reranking, grounded answer generation, one 25-example golden set, one frozen
local/mockable CI judge, retrieved-chunk snapshot storage, and one
evaluation/decision report

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Gate

- **Phase Scope**: PASS. This is `PLAN.md` Phase 5 only. It builds RAG ingestion,
  indexing, retrieval, generation, evaluation, and decision records. UI work,
  full chatbot orchestration, auth, memory, and widget behavior remain out of
  scope.
- **Layered Architecture**: PASS. Scripts trigger long-running workflows.
  Services own ingestion, chunking, retrieval, reranking, generation, and
  evaluation workflows. Repositories own PostgreSQL/pgvector persistence. Infra
  owns embedding, reranker, generator, judge, tracing, and redaction adapters.
- **FastAPI Resource Management**: PASS. Any API-facing RAG service uses lifespan
  resources and dependency injection for settings, sessions, repositories, and
  model/LLM clients. No expensive resources are created at import time or per
  request.
- **Async Safety**: PASS. API-facing database, model-server, and LLM paths use
  async clients with explicit timeouts. Long-running ingestion, embedding, and
  evaluation are kept in scripts/jobs outside request paths.
- **Secrets And Redaction**: PASS. Provider credentials are optional and resolve
  through settings/Vault or test fakes. Logs, traces, eval reports, and decision
  records avoid full raw issue bodies, prompts, retrieved chunks, and secrets.
- **Observability And Errors**: PASS. RAG ingestion, embedding, retrieval,
  reranking, generation, and evaluation emit structured progress/errors with run
  IDs or request IDs where applicable. Boundary errors stay structured and do not
  expose stack traces or raw payloads.
- **AI Evidence And Eval Gates**: PASS. The plan requires a 25-example golden
  set, naive baseline, hit@5, MRR@10, faithfulness, answer relevancy, latency,
  frozen judge metadata, judge disagreement notes, non-zero thresholds, and
  `DECISIONS.md` updates.
- **Critical Tests And CI**: PASS. Tests cover chunking, filtering, retrieval
  schemas, duplicate embedding avoidance, query transformation, reranking impact,
  grounded-answer behavior, eval report completeness, and redaction leaks.
- **Simplicity**: PASS. The plan uses existing PostgreSQL/pgvector, simple
  PostgreSQL full-text sparse retrieval first, small embedding/reranker models,
  explicit scripts, and no new datastore or multi-agent workflow.

### Post-Design Recheck

- **Phase Scope**: PASS. Generated artifacts cover only Phase 5 RAG ingestion,
  indexing, retrieval, generation, eval, and decisions.
- **Layered Architecture**: PASS. Contracts separate scripts, services,
  repositories, and infra adapters.
- **FastAPI Resource Management**: PASS. Service contracts require injected
  async sessions and clients rather than import-time construction.
- **Async Safety**: PASS. API-facing retrieval/generation uses async DB/model
  access; ingestion and embedding remain script-only.
- **Secrets And Redaction**: PASS. Contracts and quickstart prohibit real
  credentials and full source payloads in logs or reports.
- **Observability And Errors**: PASS. Command and service contracts define clear
  outputs, safe failures, and request/run correlation.
- **AI Evidence And Eval Gates**: PASS. Data model, contracts, and quickstart
  require the golden set, baseline comparison, required metrics, thresholds, and
  decision record, with the CI judge strategy explicit.
- **Critical Tests And CI**: PASS. Quickstart and contracts call out tests for
  all critical RAG behavior and leakage controls.
- **Simplicity**: PASS. No complexity exceptions were introduced.

## Project Structure

### Documentation (this feature)

```text
specs/005-advanced-rag-pipeline/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── rag-commands.md
│   └── rag-service.md
└── tasks.md              # Created by /speckit.tasks, not by /speckit.plan
```

### Source Code (repository root)

```text
scripts/
├── ingest_docs.py
├── ingest_resolved_issues.py
├── build_rag_index.py
└── evaluate_rag.py

app/
├── services/
│   ├── rag_ingestion_service.py
│   ├── rag_index_service.py
│   ├── rag_retrieval_service.py
│   ├── rag_generation_service.py
│   ├── rag_evaluation_service.py
│   └── rag_snapshot_service.py
├── repositories/
│   ├── rag_chunk_repository.py
│   ├── rag_embedding_repository.py
│   └── rag_snapshot_repository.py
├── domain/
│   └── rag.py
└── infra/
    ├── embedding_client.py
    ├── reranker_client.py
    ├── rag_generation_client.py
    └── rag_judge_client.py

migrations/
data/
└── processed/
    ├── rag_doc_sources.jsonl
    ├── rag_issue_answer_sources.jsonl
    └── rag_chunks.jsonl
evals/
├── rag_golden_set.jsonl
├── rag_eval_report.json
└── eval_thresholds.yaml
artifacts/
└── rag/
    ├── baseline/
    ├── advanced/
    └── embedding_comparison.json

tests/
├── unit/
│   ├── test_rag_chunking.py
│   ├── test_rag_metadata_filtering.py
│   ├── test_rag_retrieval_schema.py
│   ├── test_rag_hybrid_scoring.py
│   ├── test_rag_query_transformation.py
│   ├── test_rag_reranking.py
│   ├── test_rag_eval_metrics.py
│   └── test_rag_redaction.py
└── integration/
    ├── test_rag_index_scripts.py
    └── test_rag_pgvector_retrieval.py

DECISIONS.md
```

**Structure Decision**: Keep ingestion, embedding, and evaluation as reproducible
scripts. Put RAG workflow behavior in services, PostgreSQL/pgvector access in
repositories, and model/provider clients in infra. Store human-reviewable
intermediate JSONL artifacts under `data/processed/`, retrieval/eval outputs
under `evals/` and `artifacts/rag/`, and final evidence-backed choices in
`DECISIONS.md`. Use a frozen local/mockable judge for CI generation metrics,
keep optional RAGAS-style metrics separate, and store only redacted bounded
retrieved-chunk snapshots.

## Complexity Tracking

No constitution violations or complexity exceptions.
