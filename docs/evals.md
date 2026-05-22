# Evals

This document records evaluation methodology, golden sets, and threshold decisions for AI/model components.

## Phase 1 Note

Phase 1 contains no AI inference, no embeddings, no LLM calls, and therefore no eval decisions.

## Phase 3: Issue Classification

### Approaches Compared

| Approach | Description | Provider |
|----------|-------------|----------|
| Classical | TF-IDF + Logistic Regression | scikit-learn |
| Transformer | DistilBERT fine-tuned on issue text | PyTorch / Transformers |
| LLM Baseline | Azure OpenAI GPT via LangChain (or fake provider) | Azure OpenAI / fake |

### Metrics

All three approaches are evaluated on the same test split using:

- **Accuracy**: Proportion of correct predictions
- **Macro-F1**: Unweighted mean F1 across classes (bug, feature, docs, question)
- **Per-class F1**: F1 for each label individually
- **Confusion matrix**: Using stable label order: bug, feature, docs, question
- **Latency**: p50 and p95 request latency in milliseconds
- **Cost**: Per-record or amortized cost for LLM provider calls (where applicable)

### Fake Provider Mode

Automated tests use `FakeClassifierProvider` which produces deterministic labels
based on a hash of input text. No real LLM credentials are required.

- Provider backend: `fake_provider`
- Deterministic: yes (same input → same output)
- Confidence: synthetic, derived from text hash
- Cost: always None

### Vault-Backed Provider

Real Azure OpenAI credentials are resolved through Vault bootstrap settings.
The `secret_source` field in approach metrics is set to `vault` for real
provider runs and `fake_provider` for test/local runs.

### LangSmith Tracing

LangSmith tracing is enabled only when a Vault-resolved `langchain_api_key` is
available. When absent, the baseline still runs locally without tracing.

All telemetry metadata is redacted before persistence using `app.infra.redaction`.

### Golden Set

The 25-example golden set is at `evals/classification_golden_set.jsonl`.

Validation rules:
- Exactly 25 examples
- At least one example per label (bug, feature, docs, question)
- Labels must be one of the four project labels

### Shared Evaluator

`scripts/evaluate_classifiers.py` produces `evals/classifier_eval_report.json`
with metrics for all completed approaches and explicit records of any skipped
approaches. Skipped approaches are never silently omitted.

### Eval Strategy (Phase 4+)

TBD when RAG and chatbot components are introduced.

## Phase 5: Advanced RAG Pipeline

### Golden Set

- **Path**: `evals/rag_golden_set.jsonl`
- **Size**: 25 examples (20 regular + 5 with hand-labeled disagreement notes)
- **Fields**: `question`, `answer`, `expected_chunks`, `source_type`, optional `disagreement_note`

### Evaluation Modes

Two modes compared on the same golden set:

| Mode | Chunking | Retrieval | Structure |
|------|----------|-----------|-----------|
| Baseline | Fixed-size naive | Pure dense (all-MiniLM-L6-v2) | `rag_chunks` table only |
| Advanced | Parent-document retriever | Weighted hybrid (sparse 0.3 + dense 0.7) + optional reranker + optional query transformation | Full RAG pipeline |

### Required Metrics

- **hit@5**: Fraction of examples where at least one expected chunk appears in the top 5 retrieved results
- **MRR@10**: Mean reciprocal rank of the first expected chunk in the top 10 results
- **Faithfulness**: Token-overlap F1 between generated answer and reference answer (frozen judge)
- **Answer relevancy**: Token-overlap F1 between generated answer and combined question + retrieved content
- **Retrieval latency**: p50/p95 in milliseconds
- **Generation latency**: p50/p95 in milliseconds
- **Embedding comparison**: Both `all-MiniLM-L6-v2` (384 dim) and `text-embedding-3-small` (1536 dim) recorded

### Judge Configuration

- **CI judge**: `TokenOverlapJudge` with `judge_id` = `token-overlap-f1-v1` (frozen, deterministic, zero-dependency)
- **Method**: Unigram F1 token-overlap between candidate and reference answers
- **Optional RAGAS**: `RagasJudgeClient` runs with real Azure OpenAI evals when `USE_RAGAS_EVALS=1`
- **RAGAS metrics**: context precision, context recall, context entity recall, noise sensitivity, faithfulness, response relevancy
- **Disagreement notes**: 5 hand-labeled examples with explicit disagreement annotations recorded in the eval report

### Threshold Gate

Stored in `evals/eval_thresholds.yaml`:

```yaml
retrieval:
  hit_at_5: 0.0
  mrr_at_10: 0.0
gate:
  advanced_must_beat_baseline: true
```

- Command fails (non-zero exit) when advanced hit@5 or MRR@10 does not exceed baseline
- `--exploratory` flag bypasses the gate for investigation
- Baseline-permissive thresholds (0.0) allow initial fixture-based testing; will be tightened with real corpus data

### Report Output

- **Path**: `evals/rag_eval_report.json`
- **Redacted**: Raw chunks, prompts, and full content stripped before persistence
- **Contents**: Report ID, baseline run, advanced run, `advanced_beats_baseline` flag, embedding comparison, limitations, disagreement notes, creation timestamp

### Golden Datasets

- Phase 3: `evals/classification_golden_set.jsonl` (25 examples, 4 labels)
- Phase 5: `evals/rag_golden_set.jsonl` (25 examples, document + issue source types)

### Threshold Decisions

Regression thresholds set in `evals/eval_thresholds.yaml`. Currently baseline-permissive (0.0); to be tightened after real corpus ingestion in production environment.

### Regression Criteria

CI regression fails when advanced hit@5 or MRR@10 falls below baseline on the UPDATED golden set with real corpus data. Current fixture-backed values are exploratory only.

## Phase 10: Production Readiness Eval Gates

### Compact Golden Sets

Phase 10 uses compact committed golden sets for CI validation, distinct from the larger Phase 3/5 evaluation datasets:

| Set | Path | Items | Labels |
|---|---|---|---|
| Classifier golden | `evals/classification/golden.jsonl` | 25 | bug, feature, docs, question |
| RAG golden | `evals/rag/golden.jsonl` | 10 | docs, issue |

These compact sets are optimized for fast CI runs (< 15 minutes total).

### Eval Thresholds (Phase 10)

Stored in `evals/eval_thresholds.yaml` with non-zero, enabled values:

```yaml
classifier:
  accuracy_min: 0.55
  macro_f1_min: 0.50

rag:
  hit_at_5_min: 0.10
  mrr_at_10_min: 0.10
  faithfulness_min: 0.10
  answer_relevancy_min: 0.10
```

All thresholds must be present, numeric, finite, and greater than zero. Zero, missing,
NaN, negative, or non-numeric thresholds cause the validation workflow to fail before
eval runs begin.

### Eval Adapters

Two CI-specific eval adapters run against the compact golden sets:

- **`scripts/ci/run_classifier_eval.py`**: Loads `evals/classification/golden.jsonl`,
  classifies each item with a deterministic keyword-based classifier (no model loading,
  no training, no paid APIs). Computes accuracy and macro-F1, compares against
  thresholds, and writes intermediate results to `evals/reports/classifier_result.json`.

- **`scripts/ci/run_rag_eval.py`**: Loads `evals/rag/golden.jsonl`, evaluates using
  the project's `RAGEvaluationService` with `FakeGenerationClient` and
  `TokenOverlapJudge`. Computes hit@5, MRR@10, faithfulness, and answer relevancy,
  compares against thresholds, and writes intermediate results to
  `evals/reports/rag_result.json`.

Both adapters default to fake/local providers for CI speed and zero paid
credentials. Set `USE_REAL_AZURE_EVALS=1` to enable real Azure OpenAI RAG
evaluation against the live Postgres RAG index. That path resolves Azure
generation and embedding settings from Vault, uses hybrid sparse+dense
retrieval with reranking and query transformation, and fails if Azure generation
is not configured.

Set `USE_RAGAS_EVALS=1` together with `USE_REAL_AZURE_EVALS=1` to add RAGAS
judge metrics to `evals/reports/rag_result.json` and the combined
`eval_report.json`. These are recorded under `rag.ragas`; the existing manual
metrics remain the threshold-gated CI values.

Real RAG eval command:

```bash
USE_REAL_AZURE_EVALS=1 USE_RAGAS_EVALS=1 uv run python scripts/ci/run_rag_eval.py
```

### Combined Eval Report

`scripts/ci/build_eval_report.py` consumes the intermediate classifier and RAG result
files and produces `evals/reports/eval_report.json` matching the schema in
`specs/010-production-readiness/contracts/eval-report.schema.json`.

Required report fields:
- `run_id`, `timestamp`
- `classifier`: `accuracy`, `macro_f1`, `per_class_f1`, `threshold`, `passed`, `failures`
- `rag`: `hit_at_5`, `mrr_at_10`, `faithfulness`, `answer_relevancy`, `threshold`, `passed`, `failures`
- `rag.ragas` when enabled: `context_precision`, `context_recall`, `context_entity_recall`, `noise_sensitivity`, `faithfulness`, `response_relevancy`, `failures`
- `storage`: `bucket`, `key`
- `passed` (boolean — overall gating result)

### MinIO Report Storage

`scripts/ci/store_eval_report.py` stores the combined report to MinIO in CI
environments with a local filesystem fallback (`evals/reports/`) for dev/test.
The storage adapter (`scripts/ci/report_storage.py`) provides:
- `store_report()`: MinIO with local fallback
- `find_previous_green_report()`: Finds most recent passing report
- `try_load_minio()`: Optional MinIO retrieval with safe None fallback

### Previous-Green Regression Diffing

`scripts/ci/compare_previous_green_report.py` compares the current eval report
against the most recent passing "green" report. Any tracked metric that drops by
more than 2 absolute percentage points triggers a workflow failure with a safe
comparison summary naming the regressing metric(s) and their values.

Tracked metrics compared:
- Classifier: `accuracy`, `macro_f1`
- RAG: `hit_at_5`, `mrr_at_10`, `faithfulness`, `answer_relevancy`

### Eval Gate Order in Validation Workflow

1. `check_eval_thresholds.py` — thresholds exist, are enabled, and are non-zero
2. `run_evals.sh classifier` — classifier eval against compact golden set
3. `run_evals.sh rag` — RAG eval against compact golden set
4. `build_eval_report.py` — combined report generation
5. `compare_previous_green_report.py` — regression diffing
6. `store_eval_report.py` — MinIO storage
