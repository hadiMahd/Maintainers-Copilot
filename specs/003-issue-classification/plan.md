# Implementation Plan: Issue Classification Track

**Branch**: `003-issue-classification` | **Date**: 2026-05-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-issue-classification/spec.md`

## Summary

Build the Phase 3 issue classification track for Maintainer's Copilot. The work
compares a scikit-learn classical baseline, a fine-tuned DistilBERT classifier,
and an Azure OpenAI LLM baseline on the same Phase 2 test split; emits one
shared evaluation report; records deployable evidence through MLflow,
training-data hashes, artifact hashes, training plots, and MinIO artifact
references; resolves real provider and tracing secrets through Vault bootstrap
settings; redacts telemetry and artifact metadata before persistence; updates
`DECISIONS.md` with an evidence-based model choice; and exposes a model-server
classifier endpoint that loads the selected artifact during lifespan, never at
import time or per request.

## Technical Context

**Language/Version**: Python 3.11 or newer  
**Primary Dependencies**: scikit-learn, Hugging Face Transformers,
`distilbert-base-uncased`, safetensors, mlflow, LangChain, `AzureChatOpenAI`,
LangSmith (optional tracing when configured), existing Vault and MinIO
adapters, pydantic or existing domain models, pytest, httpx  
**Storage**: Phase 2 JSONL dataset splits; local artifact directories under
`artifacts/classifiers/`; evaluation outputs under `evals/`; MLflow tracking
metadata via a self-hosted local backend; MinIO as the artifact store for
MLflow outputs and the selected classifier artifact or manifest; redacted
metadata only in MLflow, LangSmith, model cards, and manifests  
**Testing**: pytest unit tests for metrics, hashes, model-card/run metadata,
MinIO manifest metadata, fake-provider baseline handling, Vault-backed secret
resolution, redaction behavior, oversized-input validation, and semantic-version
response schema; contract tests for classifier endpoint behavior; integration
tests for lifespan model loading, unavailable-model failures, and the latency
measurement harness  
**Target Platform**: Local Linux/container development environment, future CI,
and the model-server runtime used by later phases  
**Project Type**: ML training/evaluation scripts plus a model-server inference
endpoint  
**Performance Goals**: Comparable latency reporting for all three approaches;
classifier endpoint p95 latency of 500ms or better for one request on a warm,
preloaded single-process model-server measured across 30 sequential
representative requests; model loaded once during lifespan  
**Constraints**: All approaches must use the same Phase 2 test split; no RAG,
chatbot orchestration, widget behavior, or auth flows in this phase; no real
Azure/OpenAI credentials required in automated tests; real provider and tracing
credentials resolve from Vault bootstrap settings only; no raw secrets or full
issue payload dumps in logs, traces, model cards, manifests, or run metadata;
only hash-validated artifacts can be marked deployable or uploaded to MinIO  
**Scale/Scope**: Four labels (`bug`, `feature`, `docs`, `question`), one
classical baseline, one fine-tuned transformer, one LLM baseline, one shared
evaluator, one 25-example golden set, one selected deployable artifact, and one
classifier endpoint

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Gate

- **Phase Scope**: PASS. This plan covers Phase 3 only: classifier training,
  evaluation, artifact evidence, and classifier serving. RAG, chatbot,
  Streamlit, widget, auth, memory, and CI-release behavior remain out of scope.
- **Layered Architecture**: PASS. Training and evaluation stay in `scripts/`
  and shared modules. Runtime inference stays in `model_server/`. Routes remain
  HTTP-only; artifact loading, hash validation, and inference belong to services
  and infra adapters.
- **FastAPI Resource Management**: PASS. The classifier artifact is loaded
  during model-server lifespan and injected into request handling. No model or
  client is created at import time or per request.
- **Async Safety**: PASS. Training, evaluation, plotting, MLflow logging, and
  MinIO upload all stay out of request paths. Runtime HTTP behavior remains
  bounded and inference-only.
- **Secrets And Redaction**: PASS. Azure OpenAI and LangSmith settings are
  optional and resolved through Vault bootstrap settings. Tests use LangChain
  fake/mock providers. Reports, traces, MLflow metadata, model cards, and
  manifests must never contain raw provider keys or unnecessary full issue
  payloads.
- **Observability And Errors**: PASS. MLflow records run evidence for
  transformer training. The model-server returns typed predictions and
  structured unavailable-model errors. Request correlation remains available
  where the foundation already provides it.
- **AI Evidence And Eval Gates**: PASS. The plan requires one shared evaluation
  report, a 25-example golden set, artifact hashes, training-data hashes,
  model-card metadata, MLflow run records, plot references, MinIO references,
  and `DECISIONS.md` updates before a classifier can be selected.
- **Critical Tests And CI**: PASS. Tests cover metric calculations, hash
  validation, run metadata, endpoint schema, lifespan loading, and fake-provider
  behavior without real credentials.
- **Simplicity**: PASS. One classical baseline, one small transformer, and one
  LLM baseline are enough to answer the phase question. No multi-agent workflow
  or extra infrastructure beyond MLflow and MinIO is introduced.

## Project Structure

### Documentation (this feature)

```text
specs/003-issue-classification/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── classifier-commands.md
│   └── classifier.openapi.yaml
└── tasks.md
```

### Source Code (repository root)

```text
scripts/
├── train_classical_classifier.py
├── train_transformer_classifier.py
├── run_llm_classifier_baseline.py
├── evaluate_classifiers.py
├── upload_classifier_artifact_manifest.py
└── measure_classifier_latency.py

app/
├── services/
│   └── classifier_evaluation.py
└── infra/
    ├── redaction.py
    ├── mlflow/
    │   └── tracking.py
    ├── llm/
    │   └── classifier_baseline.py
    └── storage/
        └── classifier_artifacts.py

model_server/
├── api/
│   └── classifier.py
├── services/
│   └── classifier_service.py
├── infra/
│   └── classifier_loader.py
└── domain/
    └── classifier.py

artifacts/
└── classifiers/
    ├── classical/
    ├── transformer/
    │   └── plots/
    └── llm_baseline/

evals/
├── classification_golden_set.jsonl
└── classifier_eval_report.json

tests/
├── unit/
│   ├── test_classifier_metrics.py
│   ├── test_classifier_artifact_hash.py
│   ├── test_classifier_model_card.py
│   ├── test_classifier_run_metadata.py
│   ├── test_classifier_redaction.py
│   └── test_classifier_schemas.py
├── contract/
│   └── test_classifier_endpoint_contract.py
└── integration/
    ├── test_classifier_model_lifecycle.py
    ├── test_classifier_request_validation.py
    └── test_llm_classifier_fake_provider.py
```

**Structure Decision**: Keep training and evaluation commands in `scripts/`,
reuse shared business logic from `app/services/`, keep provider-specific and
artifact-storage code in `app/infra/`, and keep serving behavior isolated in
`model_server/`. MLflow tracking, Vault secret resolution, telemetry redaction,
and MinIO artifact handling are infrastructure concerns, not route concerns. The
model-server owns artifact loading and runtime inference only.

## Complexity Tracking

No constitution violations or complexity exceptions are planned.

## Post-Design Constitution Check

- **Phase Scope**: PASS. The design artifacts cover only classifier training,
  evaluation, artifact evidence, and classifier serving.
- **Layered Architecture**: PASS. Contracts keep scripts, shared evaluation
  logic, infra adapters, and model-server routes in separate responsibilities.
- **FastAPI Resource Management**: PASS. The API contract requires lifespan
  loading for the classifier artifact and forbids import-time or per-request
  model loading.
- **Async Safety**: PASS. Long-running training, MLflow logging, and artifact
  upload remain script-only concerns.
- **Secrets And Redaction**: PASS. Azure OpenAI and LangSmith remain optional,
  fake providers remain mandatory in tests, real secrets resolve from Vault
  bootstrap settings only, and no plan artifact requires raw secrets in logs,
  traces, model cards, or manifests.
- **Observability And Errors**: PASS. MLflow run evidence, structured endpoint
  errors, and request correlation are explicitly captured.
- **AI Evidence And Eval Gates**: PASS. All required metrics, hashes,
  training-plot references, MLflow run metadata, MinIO references, and
  decision-record updates are planned.
- **Critical Tests And CI**: PASS. Unit, contract, and integration tests cover
  the phase-critical failure paths and schema requirements.
- **Simplicity**: PASS. The plan stays within the minimal three-approach
  comparison required by the phase.
