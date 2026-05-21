# Command Contracts: Advanced RAG Pipeline

## Shared Requirements

- Commands run from the repository root.
- Commands use typed settings for paths, database connection, selected models,
  timeouts, and optional provider credentials.
- Commands fail non-zero when required inputs are missing, database migrations
  are unavailable, eval gates fail, or outputs cannot be produced.
- Commands must not print or write real provider credentials, full prompts, full
  issue bodies, or full retrieved chunk payloads.
- Commands are idempotent or safe to rerun.
- Long-running ingestion, embedding, and evaluation must not run inside API
  request paths.
- Required CI generation metrics use a frozen local/mockable judge. Optional
  RAGAS-style metrics may be added outside required CI but must be recorded
  separately.

## `python scripts/ingest_docs.py`

**Purpose**: Ingest project documentation sources into normalized RAG source and
chunk artifacts.

**Inputs**:
- Documentation source configuration.
- Project documentation files.
- Chunking configuration.

**Outputs**:
- Normalized documentation source records under
  `data/processed/rag_doc_sources.jsonl`.
- Documentation chunks in `data/processed/rag_chunks.jsonl` and/or PostgreSQL
  RAG chunk tables.

**Contract**:
- Uses structure-aware chunking, preserving headings, lists, code blocks, and
  source provenance where practical.
- Each chunk includes required metadata and a deterministic content hash.
- Empty, duplicated, malformed, or unsupported documents are reported without
  corrupting existing valid outputs.

**Failure Behavior**:
- Missing docs, invalid source paths, malformed files, and write failures produce
  clear errors.
- Partial output must not silently replace a previously valid corpus.

## `python scripts/ingest_resolved_issues.py`

**Purpose**: Ingest held-out resolved issues with maintainer answers into the RAG
corpus.

**Inputs**:
- Phase 2 held-out RAG/eval split.
- Maintainer-answer selection or annotation policy.
- Chunking configuration.

**Outputs**:
- `data/processed/rag_issue_answer_sources.jsonl`
- Issue-answer chunks in `data/processed/rag_chunks.jsonl` and/or PostgreSQL RAG
  chunk tables.

**Contract**:
- Only consumes held-out RAG/eval records and prevents overlap with classifier
  training data.
- Excludes or marks issue records without clear maintainer answers.
- Adds required issue metadata to every issue chunk.

**Failure Behavior**:
- Missing held-out data, leakage with classifier training records, or unusable
  answer records are reported with safe details.

## `python scripts/build_rag_index.py`

**Purpose**: Build or update sparse and dense retrieval indexes for the RAG
corpus.

**Inputs**:
- RAG chunks from JSONL or PostgreSQL.
- Embedding model comparison configuration.
- Selected pgvector table/index configuration.
- Sparse retrieval configuration.

**Outputs**:
- PostgreSQL RAG chunk and embedding records.
- pgvector indexes for selected embedding candidates.
- PostgreSQL full-text search fields/indexes.
- `artifacts/rag/embedding_comparison.json` when comparison data is available.

**Contract**:
- Compares at least two embedding candidates for evaluation.
- Avoids duplicate embeddings by `content_hash` plus embedding model.
- Updates sparse search records deterministically.
- Does not create embeddings or indexes in any API request path.

**Failure Behavior**:
- Missing chunks, failed embedding calls, model dimension mismatches, duplicate
  key conflicts, and database errors fail clearly and safely.

## `python scripts/evaluate_rag.py`

**Purpose**: Evaluate the naive baseline and advanced RAG pipeline on the same
25-example golden set.

**Inputs**:
- `evals/rag_golden_set.jsonl`
- Indexed RAG corpus.
- Baseline configuration.
- Advanced retrieval, reranking, query transformation, and generation
  configuration.
- Optional fake or real judge/generation provider settings.
- Frozen local/mockable judge configuration for required CI generation metrics.

**Outputs**:
- `evals/rag_eval_report.json`
- `artifacts/rag/baseline/` run artifacts.
- `artifacts/rag/advanced/` run artifacts.
- Updated data for `DECISIONS.md`.

**Report Contract**:
- Includes hit@5, MRR@10, faithfulness, answer relevancy, retrieval latency,
  generation latency, query transformation mode, reranking impact, embedding
  comparison, frozen judge identity, optional RAGAS-style metrics when
  available, and judge disagreement notes for five hand-labeled examples.
- Compares the advanced pipeline against the naive fixed-size chunking plus pure
  dense retrieval baseline using the same golden set.
- Fails the command when advanced hit@5 or MRR@10 does not beat baseline unless
  explicitly run in exploratory mode.

**Failure Behavior**:
- Missing golden examples, invalid expected evidence, unavailable retrieval
  store, provider timeout, malformed reports, or failed eval gates produce
  non-zero exits and safe error details.
