# Feature Specification: Advanced RAG Pipeline

**Feature Branch**: `005-advanced-rag-pipeline`  
**Created**: 2026-05-18  
**Status**: Draft  
**Input**: User description: "Phase 5, Build the advanced RAG pipeline."

## Clarifications

### Session 2026-05-18

- Q: Which vector retrieval store should the RAG pipeline use? → A: pgvector (PostgreSQL) — already in the Phase 1 stack; no new vector store infrastructure required.
- Q: Which two embedding model candidates should the pipeline compare? → A: `all-MiniLM-L6-v2` (local, CPU-feasible) vs Azure OpenAI `text-embedding-3-small` (cloud baseline, same provider as Phases 3/4).
- Q: What type of non-naive chunking strategy should the pipeline use? → A: Parent-document retriever — small child chunks indexed for embedding, full parent document retrieved for generation context.
- Q: How many conversations should retrieved-chunk snapshots be retained for? → A: Last 50 conversations.
- Q: What should the frozen local/mockable CI judge be for faithfulness and answer relevancy? → A: Token overlap scorer (unigram F1) — zero-dependency, deterministic, records a stable `judge_id` in the eval report.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Answer Maintainer Questions With Grounded Evidence (Priority: P1)

A maintainer can ask a project question and receive an answer grounded in project
documentation and a held-out set of resolved issues with maintainer answers.

**Why this priority**: The core value of this phase is trustworthy maintainer
question answering from project knowledge, before full chatbot orchestration or
UI work is added.

**Independent Test**: Ask representative maintainer questions from the RAG golden
set and verify that answers are supported by retrieved sources, include relevant
evidence, and avoid unsupported claims when evidence is insufficient.

**Acceptance Scenarios**:

1. **Given** project documentation and held-out resolved issue answers are
   ingested, **When** a maintainer asks a question covered by those sources,
   **Then** the system returns a grounded answer using relevant retrieved
   chunks.
2. **Given** the retrieved context does not contain enough evidence, **When** the
   system generates an answer, **Then** it reports insufficient evidence instead
   of inventing unsupported details.
3. **Given** metadata filters are supplied with a question, **When** retrieval is
   run, **Then** returned evidence respects those filters.

---

### User Story 2 - Prove The Advanced Pipeline Beats The Naive Baseline (Priority: P2)

A reviewer can compare the advanced RAG pipeline against a naive fixed-size
chunking plus pure dense retrieval baseline using the same 25-example golden set.

**Why this priority**: The project constitution requires AI decisions to be
backed by numbers. This phase is not complete unless the advanced pipeline shows
measured improvement over the baseline.

**Independent Test**: Run the RAG evaluation on the golden set and verify that
the report includes the required retrieval, generation, latency, and judge
disagreement measurements for both the naive baseline and the advanced pipeline.

**Acceptance Scenarios**:

1. **Given** a 25-example RAG golden set, **When** evaluation runs, **Then** the
   report includes hit@5, MRR@10, faithfulness, answer relevancy, retrieval
   latency, and generation latency.
2. **Given** baseline and advanced results, **When** the reviewer checks the
   report, **Then** the advanced pipeline outperforms the naive baseline on the
   required retrieval metrics and documents any generation tradeoffs.
3. **Given** five hand-labeled examples, **When** generation quality is judged,
   **Then** the report includes judge disagreement notes for those examples and
   identifies the frozen local/mockable judge used for CI.

---

### User Story 3 - Build A Repeatable Knowledge Corpus (Priority: P3)

A developer preparing the RAG corpus can repeatedly ingest project docs and
held-out resolved issue answers, chunk them with metadata, and generate
deduplicated embeddings safely.

**Why this priority**: Reliable retrieval depends on reproducible source
processing. Reviewers need to confirm that corpus creation can be rerun without
duplicating or silently changing evidence.

**Independent Test**: Run ingestion and embedding generation twice from the same
inputs and verify that the same content hashes, chunk identifiers, and embedding
records are produced without duplicates.

**Acceptance Scenarios**:

1. **Given** project documentation sources, **When** ingestion runs, **Then** docs
   are converted into chunks with required metadata.
2. **Given** held-out resolved issues with maintainer answers, **When** ingestion
   runs, **Then** issue-answer sources are converted into chunks with required
   metadata and are not mixed with classifier training data.
3. **Given** chunks that have already been embedded, **When** embedding
   generation reruns, **Then** duplicate embeddings are skipped by content hash.

---

### User Story 4 - Compare Retrieval Controls And Ranking Stages (Priority: P4)

A developer can evaluate sparse retrieval, dense retrieval, hybrid retrieval,
query transformation, metadata filtering, and reranking independently to
understand which choices improve final RAG behavior.

**Why this priority**: The deployment choice must be evidence-based, not just a
single opaque pipeline. Each retrieval control needs observable behavior.

**Independent Test**: Run retrieval with query transformation on and off, with
metadata filters applied, and with reranking enabled, then verify that returned
chunks include scores and metadata and that reranking changes at least one final
ranking.

**Acceptance Scenarios**:

1. **Given** the same query, **When** sparse, dense, and hybrid retrieval are
   compared, **Then** each result set includes scored chunks and metadata.
2. **Given** query transformation is toggled on and off, **When** evaluation
   runs, **Then** the report records separate results for each mode.
3. **Given** reranking is enabled over top-k candidates, **When** retrieval runs,
   **Then** final ranking changes for at least one controlled or golden-set
   query.

### Edge Cases

- Source documents are empty, duplicated, malformed, or unsupported: ingestion
  skips or reports them without corrupting the corpus.
- A resolved issue has no clear maintainer answer: it is excluded from the
  answerable RAG corpus or marked unusable for answer evaluation.
- A chunk matches both documentation and issue sources: source type and metadata
  remain explicit and do not collapse provenance.
- The same content appears in multiple sources: duplicate embeddings are avoided
  by content hash while preserving source metadata where needed.
- A metadata filter excludes all chunks: retrieval returns an empty result with a
  safe explanation rather than unrelated evidence.
- Query transformation hurts retrieval for a query: evaluation can disable it and
  reports the mode used.
- Reranking produces ties or no change for some queries: the final ordering is
  deterministic and the report still documents reranking impact.
- Retrieved chunks conflict with each other: grounded generation reports the
  conflict or uncertainty instead of hiding it.
- Generation cannot support an answer from retrieved evidence: the system
  returns insufficient-evidence behavior.
- Evaluation judges disagree on hand-labeled examples: disagreement notes are
  captured for the required examples.
- Source content contains secret-like strings or private issue text: logs,
  traces, and reports avoid full raw payload exposure.
- Retrieved chunks are snapshotted for later conversation review: snapshots are
  redacted, bounded, and retained only for the last 50 conversations; older snapshots are evicted.
- The optional RAGAS-style evaluator is unavailable: CI still uses the frozen
  local/mockable judge and records optional metrics as unavailable.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST ingest project documentation sources for RAG use.
- **FR-002**: The system MUST ingest a held-out slice of resolved issues that
  contain maintainer answers.
- **FR-003**: The system MUST avoid leakage between classifier training data and
  held-out RAG/evaluation issue sources.
- **FR-004**: The system MUST preprocess and chunk source content using a
  parent-document retriever strategy: small child chunks are embedded and indexed
  for retrieval; the full parent document (or parent chunk) is retrieved and
  passed to generation. Child chunk metadata MUST preserve a reference to its
  parent document identifier.
- **FR-005**: Each stored child chunk MUST include metadata for `chunk_id`,
  `parent_id`, `source_type`, `source_path` or `issue_number`, `source_url`,
  `title`, `labels`, `created_at` or `updated_at`, `chunk_index`,
  `content_hash`, and `token_count`.
- **FR-006**: Ingestion MUST be repeatable from the same inputs and safe to
  rerun.
- **FR-007**: Embedding generation MUST be repeatable and avoid duplicate
  embeddings by `content_hash`.
- **FR-008**: The system MUST compare exactly two embedding model candidates using
  the RAG evaluation data: `all-MiniLM-L6-v2` (local, CPU-feasible, 384-dim) and
  Azure OpenAI `text-embedding-3-small` (cloud, 1536-dim). The local model MUST
  be usable in automated tests without API credentials. Azure OpenAI embedding
  credentials are loaded from typed settings and are optional for tests.
- **FR-009**: The system MUST store embeddings in pgvector (PostgreSQL), which is
  already included in the Phase 1 default stack. Dense retrieval uses pgvector
  vector similarity search, sparse retrieval uses PostgreSQL `tsvector` full-text
  search, and metadata filtering uses SQL predicates over chunk metadata columns.
  No additional vector store service is introduced.
- **FR-010**: The retrieval service MUST support sparse retrieval.
- **FR-011**: The retrieval service MUST support dense retrieval.
- **FR-012**: The retrieval service MUST support hybrid retrieval with tunable
  weighting between sparse and dense signals.
- **FR-013**: The retrieval service MUST support cross-encoder reranking over
  top-k retrieved candidates.
- **FR-014**: The retrieval service MUST support query transformation that can be
  turned on or off for evaluation.
- **FR-015**: The retrieval service MUST support metadata filtering over chunk
  metadata.
- **FR-016**: Retrieval results MUST return chunks with scores and required
  metadata.
- **FR-017**: Reranking MUST change final ranking for at least one controlled or
  golden-set query, unless evaluation explicitly records why no ranking changed.
- **FR-018**: The system MUST generate grounded answers from retrieved evidence.
- **FR-019**: Grounded answer generation MUST cite or otherwise identify the
  supporting retrieved chunks and avoid unsupported claims.
- **FR-020**: The system MUST create a 25-example RAG golden set for retrieval
  and generation evaluation.
- **FR-021**: The RAG evaluation report MUST include hit@5, MRR@10,
  faithfulness, answer relevancy, retrieval latency, generation latency, and
  judge disagreement notes for five hand-labeled examples.
- **FR-021a**: CI faithfulness and answer relevancy MUST use a frozen token
  overlap scorer (unigram F1) as the local judge. This judge MUST be implemented
  as a zero-dependency local Python function with a stable `judge_id` string
  (e.g., `"token-overlap-f1-v1"`) recorded in every evaluation report. No paid
  provider credentials are required for this judge.
- **FR-021b**: Optional RAGAS-style metrics MAY be recorded outside required CI,
  but they MUST NOT replace the frozen CI judge gate.
- **FR-022**: The advanced RAG pipeline MUST be compared against a naive
  fixed-size chunking plus pure dense retrieval baseline using the same golden
  set.
- **FR-023**: The advanced RAG pipeline MUST beat the naive baseline on required
  retrieval metrics before the phase is considered complete.
- **FR-024**: `DECISIONS.md` MUST record embedding model choice, chunking choice,
  retrieval weighting, reranking impact, measured results, rejected alternatives,
  and known limitations.
- **FR-025**: Tests MUST cover chunking behavior, metadata filtering, retrieval
  result schema, duplicate embedding avoidance, and baseline-vs-advanced
  evaluation report shape.
- **FR-026**: The RAG service MUST expose a reusable operation for storing
  redacted retrieved-chunk snapshots for the last 50 conversations when invoked
  by later chat phases. Snapshots beyond the 50-conversation window MUST be
  evicted or overwritten to maintain the bounded retention limit.
- **FR-027**: Retrieved-chunk snapshots MUST be redacted and bounded before
  storage and MUST NOT include full sensitive payloads.
- **FR-028**: This phase MUST NOT implement UI work or full chatbot
  orchestration.

### Constitution Alignment *(mandatory)*

- **Phase Scope**: This is `PLAN.md` Phase 5 only. It builds the advanced RAG
  pipeline, evaluation corpus, retrieval/generation evaluation, and decision
  record. UI work, full chatbot orchestration, widget behavior, auth flows, and
  memory persistence are out of scope.
- **Architecture Boundaries**: RAG workflows belong in services. Persistence and
  retrieval-store access belong behind repository or infra ownership. External
  embedding, reranking, generation, and judging adapters belong in infra. Any
  HTTP boundary added later must remain thin and delegate to services.
- **Security And Redaction**: Documentation, issue text, maintainer answers,
  generated prompts, retrieved chunks, and evaluation traces may contain
  sensitive content. Logs, traces, reports, and decision records must avoid full
  raw payloads and use redacted or bounded context.
- **Observability And Errors**: RAG ingestion, embedding, retrieval, reranking,
  generation, and evaluation must produce structured progress, failures, and
  metrics with request or run identifiers where applicable. Caller-facing errors
  must be structured and must not include stack traces or raw source payloads.
- **Evidence And Evals**: A 25-example RAG golden set, naive baseline,
  advanced-pipeline comparison, required retrieval/generation metrics, latency
  metrics, frozen CI judge metadata, judge disagreement notes, and
  `DECISIONS.md` updates are release gates for this phase.
- **Critical Tests**: Critical tests must cover non-naive chunking,
  metadata filtering, retrieval result schemas, duplicate embedding avoidance,
  query transformation toggling, reranking impact, grounded-answer behavior,
  eval report completeness, and no raw sensitive payload leakage.

### Key Entities *(include if feature involves data)*

- **Source Document**: Project documentation item available for ingestion,
  including source path, URL when available, title, update time, and content.
- **Resolved Issue Answer Source**: Held-out issue record with maintainer answer
  content, issue number, labels, source URL, timestamps, and answerable context.
- **RAG Chunk**: Searchable content unit produced from a source document or issue
  answer source, using the parent-document retriever strategy. A child chunk is
  the small unit embedded and indexed; a parent chunk or document is the wider
  context retrieved for generation. Each child chunk carries a `parent_id`
  reference in its metadata.
- **Chunk Metadata**: Provenance and filtering data attached to each child chunk:
  `chunk_id`, `parent_id`, `source_type`, `source_path` or `issue_number`,
  `source_url`, `title`, `labels`, `created_at` or `updated_at`, `chunk_index`,
  `content_hash`, and `token_count`.
- **Embedding Candidate**: One of two candidate models evaluated for dense
  retrieval quality and latency: `all-MiniLM-L6-v2` (local, 384-dim) or Azure
  OpenAI `text-embedding-3-small` (cloud, 1536-dim).
- **Retrieval Query**: Maintainer question plus optional metadata filters and
  query transformation mode.
- **Retrieval Result**: Retrieved chunk, retrieval scores, rank, and chunk
  metadata.
- **Grounded Answer**: Answer generated from retrieved evidence, including
  supporting source references and insufficiency behavior when evidence is weak.
- **RAG Golden Example**: Evaluation example containing a maintainer question,
  expected relevant source evidence, expected answer guidance, and labels or
  notes needed for judging.
- **RAG Evaluation Report**: Results record comparing baseline and advanced
  pipeline metrics, latency, generation quality, judge disagreement notes, and
  limitations.
- **Retrieved Chunk Snapshot**: Redacted bounded record of chunks retrieved for
  a conversation, retained for the last 50 conversations for observability and
  final review. Snapshots beyond 50 are evicted.
- **RAG Decision Record**: `DECISIONS.md` section documenting selected embedding
  model, chunking strategy, retrieval weighting, reranking impact, measured
  results, and rejected alternatives.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Re-running ingestion from the same inputs produces the same chunk
  content hashes and no duplicate chunk records.
- **SC-002**: Re-running embedding generation skips 100% of chunks whose
  `content_hash` already has an embedding for the selected embedding candidate.
- **SC-003**: The RAG golden set contains exactly 25 examples and includes both
  documentation-backed and issue-answer-backed questions.
- **SC-004**: The evaluation report includes hit@5, MRR@10, faithfulness, answer
  relevancy, retrieval latency, and generation latency for the naive baseline and
  advanced pipeline.
- **SC-005**: The advanced pipeline achieves higher hit@5 and higher MRR@10 than
  the naive fixed-size chunking plus pure dense retrieval baseline on the same
  golden set.
- **SC-006**: Retrieval results for non-empty queries include rank, score,
  content preview or chunk reference, and complete required metadata for 100% of
  returned chunks.
- **SC-007**: Metadata filter tests demonstrate correct include/exclude behavior
  for source type, issue or document identity, labels, and timestamps.
- **SC-008**: Query transformation can be evaluated in both enabled and disabled
  modes, with separate metrics recorded.
- **SC-009**: Reranking changes the final ranking for at least one controlled or
  golden-set query and its impact is recorded in the evaluation report.
- **SC-010**: Five hand-labeled golden examples include documented judge
  disagreement notes.
- **SC-011**: The RAG eval report records the frozen token overlap scorer
  (`judge_id: "token-overlap-f1-v1"`) as the CI judge identity and any optional
  RAGAS-style metrics separately.
- **SC-012**: Retrieved-chunk snapshot tests prove stored snapshots are redacted,
  bounded, and associated with conversation metadata without raw full chunks.
- **SC-013**: Grounded answers cite or identify supporting evidence for all
  answerable examples and return insufficient-evidence behavior for unanswerable
  examples.
- **SC-014**: `DECISIONS.md` contains the selected embedding model, chunking
  strategy, retrieval weighting, reranking impact, measured results, rejected
  alternatives, and limitations before the phase is considered complete.

## Assumptions

- The held-out resolved issue slice comes from Phase 2 processed data and remains
  separate from classifier training data and other held-out evaluation data.
- The naive baseline is fixed-size chunking plus pure dense retrieval without
  hybrid weighting, query transformation, metadata filtering, or reranking.
- The vector retrieval store is pgvector (PostgreSQL), already in the Phase 1 stack. Embedding model candidates will be finalized during planning.
- The first implementation may use bounded local or external generation and
  judging providers, but automated tests must not require real secrets.
- RAG answers are intended for later chatbot use, but this phase exposes the
  pipeline and evaluation behavior without building full chatbot orchestration
  or UI.
