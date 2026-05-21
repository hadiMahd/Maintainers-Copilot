# Implementation Plan: Dataset Pipeline

**Branch**: `002-dataset-pipeline` | **Date**: 2026-05-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-dataset-pipeline/spec.md`

## Summary

Build the Phase 2 reproducible dataset pipeline for Maintainer's Copilot. The
pipeline will select one public open-source repository through configuration,
fetch closed GitHub issues and comments, store raw data as JSONL, preprocess
records into the four project labels, create deterministic temporal splits,
generate dataset statistics, and document repository, label mapping, split
policy, limitations, and risks in `DECISIONS.md`. This phase produces scripts and
data artifacts only; it does not train models, build embeddings, implement RAG
retrieval, or add database persistence.

## Technical Context

**Language/Version**: Python 3.11 or newer  
**Primary Dependencies**: httpx for GitHub API access with timeouts and
pagination, pydantic-settings for typed settings, PyYAML or JSON parsing for
label mapping configuration, pytest for mapping and split tests  
**Storage**: JSONL files under `data/raw/` and `data/processed/`; YAML or JSON
configuration under `configs/` or an equivalent config directory  
**Testing**: pytest unit tests for label mapping, schema validation, deterministic
splits, temporal split invariants, leakage checks, and settings behavior  
**Target Platform**: Local developer environment and future CI jobs  
**Project Type**: Script-based dataset pipeline extending the Phase 1 backend
foundation  
**Performance Goals**: Safe reruns; bounded GitHub API requests with timeouts and
pagination; deterministic outputs for unchanged inputs  
**Constraints**: No notebooks as official pipeline; no real secrets in scripts,
fixtures, reports, or artifacts; optional GitHub token loaded only through typed
settings; no model training, embeddings, RAG retrieval, or required database
persistence  
**Scale/Scope**: One configured public repository, four mapped labels (`bug`,
`feature`, `docs`, `question`), raw issue/comment artifacts, processed labeled
artifact, train/validation/test/held-out split artifacts, and a dataset report

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Gate

- **Phase Scope**: PASS. This is `PLAN.md` Phase 2 only. It produces scripts and
  data artifacts and excludes training, embeddings, RAG retrieval, auth, memory,
  chatbot behavior, UI work, and widget work.
- **Layered Architecture**: PASS. Pipeline scripts may reuse foundation settings
  and domain validation, but no API routes own dataset workflow logic.
- **FastAPI Resource Management**: PASS. No web request path changes are planned.
  The pipeline is script-based and does not create app resources at import time.
- **Async Safety**: PASS. GitHub calls use httpx with explicit timeouts and
  pagination; no async route path is affected.
- **Secrets And Redaction**: PASS. GitHub token is optional, local-only, loaded
  through typed settings, and never written to artifacts, docs, logs, or reports.
- **Observability And Errors**: PASS. Scripts must return clear progress and
  failure messages and exit non-zero when required outputs cannot be produced.
- **AI Evidence And Eval Gates**: PASS. This phase creates dataset statistics and
  `DECISIONS.md` evidence for future classifier and RAG phases; it makes no model
  quality claims.
- **Critical Tests And CI**: PASS. Tests cover label mapping, record schemas,
  deterministic splits, temporal invariants, leakage prevention, and secret
  hygiene.
- **Simplicity**: PASS. The design uses explicit scripts and JSONL artifacts,
  avoids notebooks as the official path, and adds no heavy infrastructure.

### Post-Design Recheck

- **Phase Scope**: PASS. `research.md`, `data-model.md`, contracts, and
  quickstart cover only dataset ingestion, preprocessing, splitting, reporting,
  and documentation.
- **Layered Architecture**: PASS. Data entities are file-based pipeline concepts;
  no API route or persistence layer changes are required.
- **FastAPI Resource Management**: PASS. No FastAPI resource ownership changes
  are introduced.
- **Async Safety**: PASS. Command contracts require GitHub timeouts and clear
  rate-limit failures; no request path is changed.
- **Secrets And Redaction**: PASS. Artifacts explicitly prohibit writing tokens or
  real secrets and discourage full issue/comment dumps in routine logs.
- **Observability And Errors**: PASS. Command contracts specify outputs, failure
  behavior, and reproducibility expectations.
- **AI Evidence And Eval Gates**: PASS. Dataset report and `DECISIONS.md` are
  required evidence for future phases.
- **Critical Tests And CI**: PASS. Quickstart and contracts include mapping,
  schema, split, leakage, safe-rerun, and secret-hygiene checks.
- **Simplicity**: PASS. No complexity exceptions were introduced.

## Project Structure

### Documentation (this feature)

```text
specs/002-dataset-pipeline/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── dataset-pipeline-commands.md
└── tasks.md              # Created by /speckit.tasks, not by /speckit.plan
```

### Source Code (repository root)

```text
scripts/
├── fetch_issues.py
├── fetch_issue_comments.py
├── preprocess_issues.py
├── make_splits.py
└── dataset_report.py

configs/
├── dataset.yml
└── label_mapping.yml

data/
├── raw/
│   └── issues.jsonl
└── processed/
    ├── issues_labeled.jsonl
    ├── train.jsonl
    ├── validation.jsonl
    ├── test.jsonl
    ├── heldout_rag_eval.jsonl
    └── dataset_report.json

tests/
├── unit/
│   ├── test_label_mapping.py
│   ├── test_dataset_schemas.py
│   └── test_split_policy.py
└── integration/
    └── test_dataset_pipeline_commands.py

DECISIONS.md
```

**Structure Decision**: Keep Phase 2 as a script-first pipeline under
`scripts/`, with configuration in `configs/`, JSONL artifacts under `data/`, and
tests under `tests/`. Reuse Phase 1 typed settings and domain validation patterns
where they exist, but do not introduce API routes, database persistence, notebooks
as the official path, or model/RAG functionality.

## Complexity Tracking

No constitution violations or complexity exceptions.
