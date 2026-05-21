# Research: Advanced RAG Pipeline

## Decision: Use PostgreSQL with pgvector as the retrieval store

**Rationale**: The Phase 1 foundation already selected PostgreSQL 16 with
pgvector, and no prior project artifact selected Qdrant. pgvector keeps chunk
metadata, sparse fields, and dense embeddings in the existing database boundary
and avoids adding another datastore for a bootcamp project.

**Alternatives considered**:
- Qdrant: rejected because the project has not selected it and adding another
  datastore increases local setup and operational complexity.
- File-only vector indexes: rejected because metadata filtering, reruns, and
  future API-backed retrieval are easier to defend with database persistence.

## Decision: Use PostgreSQL full-text search for the first sparse retrieval path

**Rationale**: PostgreSQL full-text search is already available with the selected
database and can support a simple sparse signal without introducing another
search engine. It can be combined with dense scores and metadata filters in one
repository layer.

**Alternatives considered**:
- BM25 through a lightweight local library: acceptable fallback for offline
  experiments, but less direct for API-backed filtering and persistence.
- External search service: rejected because it adds infrastructure outside the
  current phase needs.

## Decision: Use a parent-document retriever instead of naive fixed-size chunks

**Rationale**: Documentation headings, code blocks, lists, and issue-answer
conversation boundaries carry meaning. The chosen parent-document retriever
stores small child chunks for embedding and retrieval while preserving a parent
document boundary for grounded answer context. That produces a defensible
contrast against the naive baseline and matches the Phase 5 requirement that
retrieved children carry a stable `parent_id`.

**Alternatives considered**:
- Fixed-size chunks only: kept as the baseline but rejected for the advanced
  pipeline because it ignores source structure.
- LLM-generated chunking: rejected for v1 because it adds cost, non-determinism,
  and extra secret/provider needs.

## Decision: Compare at least two small embedding candidates

**Rationale**: Embedding model choice is a required AI decision. Small local or
downloadable candidates keep the experiment practical while producing real
numbers for hit@5, MRR@10, and latency.

**Alternatives considered**:
- One default embedding model: rejected because the spec requires comparison.
- Large embedding models only: rejected because they make local development and
  CI harder for a bootcamp project.

## Decision: Avoid duplicate embeddings by content hash plus embedding model

**Rationale**: The same chunk text can appear across reruns or sources. Deduping
by `content_hash` and embedding candidate prevents redundant storage while still
allowing model comparisons.

**Alternatives considered**:
- Deduplicate by chunk ID only: rejected because chunk IDs can change when source
  paths or indexes change.
- Deduplicate by text prefix: rejected because it is not collision-resistant
  enough for reproducibility checks.

## Decision: Combine dense and sparse retrieval with normalized weighted scoring

**Rationale**: Dense search captures semantic similarity while sparse search
preserves exact maintainer terms, file paths, error codes, and package names.
Normalizing each score family and tuning a simple weight creates an explainable
hybrid ranker.

**Alternatives considered**:
- Pure dense retrieval: kept as part of the naive baseline but rejected as the
  advanced default because exact technical terms matter.
- Learned rank fusion: rejected because it needs more training data than this
  phase provides.

## Decision: Use a small cross-encoder reranker over top-k candidates

**Rationale**: A small cross-encoder can improve final ordering after retrieval
without replacing the retrieval stack. Applying it only to top-k candidates keeps
latency bounded and makes reranking impact measurable.

**Alternatives considered**:
- Rerank all chunks: rejected because it is too slow.
- No reranker: rejected because the phase explicitly requires reranking and
  reranking impact.

## Decision: Make query transformation optional and evaluation-controlled

**Rationale**: Query transformation can help ambiguous maintainer questions but
can also hurt exact technical queries. The evaluation must record enabled and
disabled modes separately so the final decision is evidence-based.

**Alternatives considered**:
- Always transform queries: rejected because it can obscure exact error codes,
  file paths, or package names.
- Never transform queries: rejected because the phase requires query
  transformation.

## Decision: Generate answers only from retrieved evidence and expose insufficiency

**Rationale**: Maintainer answers must be grounded. If retrieved chunks do not
support an answer, the generator should say that evidence is insufficient rather
than filling gaps.

**Alternatives considered**:
- Answer from model prior knowledge: rejected because it undermines faithfulness.
- Return only retrieved chunks: useful for debugging, but the phase requires
  grounded answer generation.

## Decision: Use one RAG eval report comparing baseline and advanced runs

**Rationale**: A single report makes review straightforward and prevents
selective comparison. It should contain retrieval metrics, generation metrics,
latencies, reranking impact, query-transformation mode, judge disagreement notes,
and limitations.

**Alternatives considered**:
- Separate ad hoc reports per run: rejected because comparisons become fragile.
- Markdown-only report: rejected because JSON is easier to validate in tests and
  CI.

## Decision: Use a frozen local/mockable judge for CI generation metrics

**Rationale**: The project brief allows RAGAS or a frozen judge. Required CI
must be deterministic and independent of paid API credentials, so faithfulness
and answer relevancy gates use a frozen local/mockable judge. Optional
RAGAS-style metrics can be recorded separately when available, but they do not
replace the CI judge gate.

**Alternatives considered**:
- Live LLM judge in CI: rejected because it is credential-dependent, costly, and
  less deterministic.
- Retrieval-only evals: rejected because the phase requires generation metrics.

## Decision: Store redacted retrieved-chunk snapshots for recent conversations

**Rationale**: The project brief requires per-conversation retrieved-chunk
snapshots for the last 50 conversations. The RAG service provides a snapshot
operation that stores chunk IDs, scores, metadata, and redacted previews so
Phase 7 can call it after RAG tool use without rerunning ingestion or indexing.

**Alternatives considered**:
- Store full raw chunks: rejected because retrieved content can contain
  sensitive issue text.
- Defer all snapshot behavior to the chatbot phase: rejected because RAG owns
  the retrieval result schema and redaction boundary for chunk evidence.
