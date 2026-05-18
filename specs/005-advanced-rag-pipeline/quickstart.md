# Quickstart: Advanced RAG Pipeline

## Prerequisites

- Phase 1 foundation exists with PostgreSQL 16 and pgvector available through
  local Docker Compose or equivalent local setup.
- Phase 2 processed splits exist, including held-out RAG/eval records.
- Real provider credentials are not required for automated tests; fake providers
  or local adapters must be available for generation/judging tests.
- Required CI generation metrics use a frozen local/mockable judge; optional
  RAGAS-style metrics may be recorded separately when available.
- Database migrations for RAG chunks, embeddings, full-text search fields, and
  pgvector indexes are applied before indexing or retrieval.

## Ingest Project Documentation

Run:

```bash
python scripts/ingest_docs.py
```

Expected result: project documentation sources are normalized and chunked with
required metadata. Re-running with unchanged inputs produces the same content
hashes and no duplicate chunk records.

## Ingest Held-Out Resolved Issues

Run:

```bash
python scripts/ingest_resolved_issues.py
```

Expected result: held-out issue records with maintainer answers are normalized
and chunked. The command rejects leakage with classifier training data and skips
issues without clear maintainer answers according to the documented policy.

## Build The RAG Index

Run:

```bash
python scripts/build_rag_index.py
```

Expected result: chunks and metadata are stored in PostgreSQL, dense embeddings
are stored with pgvector, sparse search fields are updated, at least two
embedding candidates are compared, and duplicate embeddings are skipped by
`content_hash` plus embedding model.

## Evaluate Baseline And Advanced RAG

Run:

```bash
python scripts/evaluate_rag.py
```

Expected result: `evals/rag_eval_report.json` compares the naive fixed-size
chunking plus pure dense retrieval baseline against the advanced pipeline. The
report includes hit@5, MRR@10, faithfulness, answer relevancy, retrieval latency,
generation latency, embedding comparison, query transformation mode, reranking
impact, frozen judge identity, optional RAGAS-style metrics when available, and
judge disagreement notes for five hand-labeled examples.

## Validate Retrieved-Chunk Snapshots

Call the RAG snapshot service with a representative retrieval result.

Expected result: the stored snapshot includes conversation/message/trace
metadata, chunk IDs, scores, and redacted previews only. Full raw chunks and
secret-like values are not stored, and last-N retention is enforced.

## Validate Query Transformation Modes

Run evaluation with query transformation enabled and disabled.

Expected result: the report records separate mode results so reviewers can see
whether transformation helps or hurts the golden set.

## Validate Metadata Filtering

Run retrieval or evaluation cases with source type, label, issue number, source
path, and timestamp filters.

Expected result: returned chunks respect filters. Filters that exclude all
chunks produce an empty result with safe explanation.

## Validate Reranking Impact

Run retrieval with reranking enabled over top-k candidates.

Expected result: at least one controlled or golden-set query has a changed final
ranking, and the ranking change plus metric impact are recorded.

## Run Critical Tests

Run:

```bash
python -m pytest tests/unit/test_rag_chunking.py
python -m pytest tests/unit/test_rag_metadata_filtering.py
python -m pytest tests/unit/test_rag_retrieval_schema.py
python -m pytest tests/unit/test_rag_hybrid_scoring.py
python -m pytest tests/unit/test_rag_query_transformation.py
python -m pytest tests/unit/test_rag_reranking.py
python -m pytest tests/unit/test_rag_eval_metrics.py
python -m pytest tests/unit/test_rag_redaction.py
python -m pytest tests/unit/test_rag_snapshot_service.py
```

Expected result: chunking, filtering, retrieval schemas, hybrid scores, query
transformation toggles, reranking, metrics, snapshot retention, and redaction
expectations pass.

## Update Decisions

Update `DECISIONS.md` with:

- selected embedding model and comparison numbers
- selected chunking strategy and baseline comparison
- selected sparse/dense hybrid weighting
- reranking impact
- generation behavior and insufficiency policy
- frozen CI judge choice and optional RAGAS-style metric policy
- required metrics from `evals/rag_eval_report.json`
- rejected alternatives and limitations

Expected result: reviewers can verify that embedding, chunking, retrieval
weighting, reranking, and generation decisions are backed by numbers.
