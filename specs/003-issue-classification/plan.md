# Implementation Plan: Issue Classification Track

**Branch**: `003-issue-classification` | **Date**: 2026-05-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-issue-classification/spec.md`

## Summary

Build the Phase 3 issue classification track for Maintainer's Copilot. The work
compares a scikit-learn classical baseline, a fine-tuned Hugging Face transformer,
and an LLM baseline on the same Phase 2 test split; emits comparable metrics and
JSON artifacts; creates a 25-example golden set; saves transformer artifacts with
model card, metrics, training data hash, artifact SHA-256, training run logs,
training plots, and MinIO artifact or manifest references; records the
evidence-based classifier decision in `DECISIONS.md`; and exposes a model-server
classifier endpoint that loads the selected model during lifespan, never at
import time or per request.

## Technical Context

**Language/Version**: Python 3.11 or newer  
**Primary Dependencies**: scikit-learn for the classical baseline and metrics,
Hugging Face Transformers for the fine-tuned small encoder, safetensors when
practical for model weights, pytest for tests, httpx for model-server contract
tests, pydantic or existing domain models for typed schemas, and a local
MLflow-style or structured file run logger for transformer training  
**Storage**: Phase 2 JSONL dataset splits; JSON metrics, predictions, model
cards, and reports under `artifacts/` and `evals/`; classifier model artifacts
under `artifacts/classifiers/`; training plots under the transformer artifact;
selected classifier artifact or manifest stored in MinIO for final review  
**Testing**: pytest unit tests for metrics, hash validation, model-card schema,
run-log metadata, training plot references, MinIO manifest metadata, prediction
schemas, unavailable-model errors, and model-server lifecycle behavior; contract
tests for classifier endpoint response shape  
**Target Platform**: Local developer environment and future CI jobs; model-server
runtime for classifier inference  
**Project Type**: ML training/evaluation scripts plus model-server inference
endpoint  
**Performance Goals**: Comparable latency reporting for all approaches; model
loaded once during model-server lifespan; no training or model loading in request
paths  
**Constraints**: Same Phase 2 test split for all approaches; no RAG, chatbot
orchestration, widget work, or production auth; LLM provider credentials optional
and never required for tests; no raw secrets or unnecessary full issue payloads
in logs/reports  
**Scale/Scope**: Four labels (`bug`, `feature`, `docs`, `question`), one
classical baseline, one fine-tuned lightweight transformer, one LLM baseline, one
shared evaluator, one classifier serving endpoint, and one evidence-backed
decision record

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Gate

- **Phase Scope**: PASS. This is `PLAN.md` Phase 3 only. It compares classifier
  approaches, emits artifacts, and exposes the classifier model-server endpoint;
  it excludes RAG, chatbot orchestration, widget work, and unrelated product
  features.
- **Layered Architecture**: PASS. Training and evaluation live in scripts/shared
  modules. Runtime serving lives in `model_server/api/classifier.py` and related
  model-server services/infra; routes stay thin.
- **FastAPI Resource Management**: PASS. The classifier model is loaded during
  model-server lifespan and is not loaded at import time or per request.
- **Async Safety**: PASS. Training stays out of request paths. Model-server route
  work is inference-only and uses preloaded resources.
- **Secrets And Redaction**: PASS. LLM baseline credentials are optional local
  settings or test fakes. Reports and logs must not contain provider keys or raw
  secrets.
- **Observability And Errors**: PASS. Commands emit clear progress/failure
  messages. Model-server endpoint returns typed predictions or structured
  unavailable-model errors.
- **AI Evidence And Eval Gates**: PASS. Required metrics, model cards, hashes,
  training run logs, training plots, MinIO artifact references, golden set,
  evaluation report, and `DECISIONS.md` comparison are central to the plan.
- **Critical Tests And CI**: PASS. Tests cover metric calculations, report shape,
  artifact hash validation, model-server schemas, lifecycle rules, and no real
  secret leakage.
- **Simplicity**: PASS. Use one classical baseline, one lightweight transformer,
  and one LLM baseline without multi-agent workflows or extra infrastructure.

### Post-Design Recheck

- **Phase Scope**: PASS. Research, data model, contracts, and quickstart cover
  only classifier training, evaluation, artifact metadata, and classifier serving.
- **Layered Architecture**: PASS. Contracts separate scripts from model-server
  endpoint behavior and keep training outside request paths.
- **FastAPI Resource Management**: PASS. The API contract requires lifespan model
  loading and structured unavailable-model behavior.
- **Async Safety**: PASS. No long-running training/evaluation is introduced into
  runtime endpoints.
- **Secrets And Redaction**: PASS. LLM credentials remain optional; fake provider
  is required for automated tests.
- **Observability And Errors**: PASS. Command and endpoint contracts define clear
  outputs, typed responses, and controlled failures.
- **AI Evidence And Eval Gates**: PASS. Artifacts and reports include comparable
  metrics, cost where applicable, model/training hashes, run IDs, training plot
  references, MinIO references, and decision records.
- **Critical Tests And CI**: PASS. Quickstart and contracts call out metrics,
  schema, hash, lifecycle, and unavailable-model checks.
- **Simplicity**: PASS. No complexity exceptions were introduced.

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
└── tasks.md              # Created by /speckit.tasks, not by /speckit.plan
```

### Source Code (repository root)

```text
scripts/
├── train_classical_classifier.py
├── train_transformer_classifier.py
├── evaluate_classifiers.py
├── run_llm_classifier_baseline.py
└── upload_classifier_artifact_manifest.py

app/
└── services/
    └── classifier_evaluation.py

model_server/
├── api/
│   └── classifier.py
├── services/
│   └── classifier_service.py
└── domain/
    └── classifier.py

evals/
├── classification_golden_set.jsonl
└── classifier_eval_report.json

artifacts/
└── classifiers/
    ├── classical/
    ├── transformer/
    │   └── plots/
    └── llm_baseline/

tests/
├── unit/
│   ├── test_classifier_metrics.py
│   ├── test_classifier_artifact_hash.py
│   └── test_classifier_schemas.py
├── contract/
│   └── test_classifier_endpoint_contract.py
└── integration/
    └── test_classifier_model_lifecycle.py

DECISIONS.md
```

**Structure Decision**: Keep all training/evaluation commands under `scripts/`.
Use a shared evaluation module for metrics and report shaping. Keep runtime
inference in the model server under `model_server/`, with model loading owned by
lifespan and route code limited to request/response mapping. Store classifier
artifacts under `artifacts/classifiers/` and classifier evaluation outputs under
`evals/`. Transformer training must write a run-log record and plots, then store
the selected classifier artifact or a manifest in MinIO for final review.

## Complexity Tracking

No constitution violations or complexity exceptions.
