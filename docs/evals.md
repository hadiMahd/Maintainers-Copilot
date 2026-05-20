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
- **Optional RAGAS**: `NonCIJudgeStub` — config seam, raises `NotImplementedError` when no real RAGAS provider is available
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
