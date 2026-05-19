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

## Golden Datasets

- Phase 3: `evals/classification_golden_set.jsonl` (25 examples, 4 labels)

## Threshold Decisions (TBD)

Regression thresholds will be set after the classifier comparison is complete.

## Regression Criteria (TBD)

CI regression criteria will be defined after threshold thresholds are established.
