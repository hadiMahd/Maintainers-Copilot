# Quickstart: Advanced RAG Pipeline

## Prerequisites

- Phase 1 foundation exists with PostgreSQL 16 and pgvector available through
  local Docker Compose or equivalent local setup.
- Real provider credentials are not required for automated tests; fake providers
  or local adapters must be available for generation/judging tests.
- Required CI generation metrics use a frozen local/mockable judge; optional
  RAGAS-style metrics may be recorded separately when available.

## Ingest Project Documentation

Run:

```bash
uv run python scripts/ingest_docs.py
```

Expected result: project documentation sources (from `docs/*.md`) are normalized
and chunked with required metadata. Outputs: `data/processed/rag_doc_sources.jsonl`
and appends to `data/processed/rag_chunks.jsonl`. Re-running with unchanged inputs
produces the same content hashes and no duplicate chunk records.

## Ingest Held-Out Resolved Issues

Run:

```bash
uv run python scripts/ingest_resolved_issues.py --input <issues.jsonl> [--classifier-source-ids <path>]
```

Expected result: held-out issue records with maintainer answers are normalized
and chunked. Outputs: `data/processed/rag_issue_answer_sources.jsonl` and appends
to `data/processed/rag_chunks.jsonl`. The `--classifier-source-ids` flag
prevents leakage with classifier training data.

## Build The RAG Index

Run:

```bash
uv run python scripts/build_rag_index.py
```

For testing with deterministic fake embeddings (no real model required):
```bash
uv run python scripts/build_rag_index.py --fake
```

Expected result: chunks are embedded, duplicate embeddings skipped by
`content_hash` plus embedding model. Output: `artifacts/rag/embedding_comparison.json`
with both `all-MiniLM-L6-v2` and `text-embedding-3-small` candidates recorded.

## Evaluate Baseline And Advanced RAG

Run:

```bash
uv run python scripts/evaluate_rag.py --exploratory
```

Expected result: `evals/rag_eval_report.json` compares the naive fixed-size
chunking plus pure dense retrieval baseline against the advanced pipeline. The
report includes:
- hit@5, MRR@10, faithfulness, answer relevancy, retrieval latency (p50/p95),
  generation latency (p50/p95)
- Embedding comparison: `all-MiniLM-L6-v2` (384 dim) vs `text-embedding-3-small` (1536 dim)
- Frozen judge identity: `token-overlap-f1-v1`
- Judge disagreement notes for 5 hand-labeled examples
- Query transformation mode and reranking impact when enabled
- `--exploratory` bypasses the threshold gate (advanced must beat baseline on
  hit@5 and MRR@10 when not in exploratory mode)

## Validate Retrieved-Chunk Snapshots

Call the RAG snapshot service (`RAGSnapshotService`) with a representative
retrieval result set. Expected: stored snapshot includes conversation/message/trace
metadata, chunk IDs, scores, and redacted previews only. Full raw chunks and
secret-like values are not stored. Last-50-conversation retention enforced.

## Validate Query Transformation Modes

Set `RetrievalQuery.query_transformation_enabled = True/False` when calling the
retrieval service. Expected: transformation expands technical terms in the query
when enabled; passes through unchanged when disabled. Eval reports record the
transformation mode.

## Validate Metadata Filtering

Set `RetrievalQuery.metadata_filters` with `source_type`, `source_path`, or
`labels` fields. Expected: returned chunks respect filters. Filters that exclude
all chunks produce an empty result with a safe explanation string.

## Validate Reranking Impact

Set `RetrievalQuery.reranking_enabled = True` and ensure a `CrossEncoderReranker`
or `FakeRerankerClient` is wired into the retrieval service. Expected: top-k
candidates are rescored, final ordering may change, and `rerank_score` is
populated on each `RetrievalResult`.

## Run Critical Tests

Run:

```bash
uv run pytest tests/unit/test_rag_chunking.py -v
uv run pytest tests/unit/test_rag_metadata_filtering.py -v
uv run pytest tests/unit/test_rag_hybrid_scoring.py -v
uv run pytest tests/unit/test_rag_query_transformation.py -v
uv run pytest tests/unit/test_rag_reranking.py -v
uv run pytest tests/unit/test_rag_eval_metrics.py -v
uv run pytest tests/unit/test_rag_redaction.py -v
uv run pytest tests/unit/test_rag_snapshot_service.py -v
uv run pytest tests/unit/test_rag_provider_resolution.py -v
uv run pytest tests/unit/test_rag_observability.py -v
uv run pytest tests/contract/test_rag_service_contract.py -v
uv run pytest tests/contract/test_rag_commands.py -v
uv run pytest tests/integration/test_rag_grounded_answers.py -v
uv run pytest tests/integration/test_rag_index_scripts.py -v
uv run pytest tests/integration/test_rag_pgvector_retrieval.py -v
```

Or run all Phase 5 tests together:
```bash
uv run pytest tests/unit/test_rag_*.py tests/contract/test_rag_*.py tests/integration/test_rag_*.py -v -q
```

Expected result: 60+ Phase 5 tests pass (all fixture-backed, no real DB or
credentials required).

## Artifacts Produced

| Path | Description |
|------|-------------|
| `data/processed/rag_doc_sources.jsonl` | Normalized documentation source records |
| `data/processed/rag_issue_answer_sources.jsonl` | Normalized issue-answer source records |
| `data/processed/rag_chunks.jsonl` | All parent-document child chunks |
| `artifacts/rag/embedding_comparison.json` | Two-candidate embedding comparison |
| `evals/rag_golden_set.jsonl` | 25-example RAG golden set |
| `evals/rag_eval_report.json` | Redacted baseline-vs-advanced evaluation report |
| `evals/eval_thresholds.yaml` | Eval threshold configuration |

## Update Decisions

Update `DECISIONS.md` with:
- Selected chunking strategy (parent-document retriever)
- Sparse/dense/hybrid retrieval with weighted scoring
- Cross-encoder reranker model and config seam
- Embedding model comparison numbers
- Token-overlap CI judge identity and optional RAGAS policy
- Snapshot redaction and retention policy
- Eval gate behavior and exploratory mode
- Classifier data leakage prevention

Expected result: reviewers can verify that all RAG architectural decisions are
backed by measured evidence and documented tradeoffs.
