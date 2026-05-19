# Quickstart: Issue Classification Track

## Prerequisites

- Phase 2 dataset splits exist and contain only `bug`, `feature`, `docs`, and
  `question` labels.
- Local configuration contains no real provider credentials unless intentionally
  running a real LLM baseline locally.
- Automated tests can use fake LLM provider mode.

## Train The Classical Baseline

Run:

```bash
python scripts/train_classical_classifier.py
```

Expected result: a classical model artifact, predictions, and metrics are written
under `artifacts/classifiers/classical/`.

## Train The Transformer Classifier

Run:

```bash
python scripts/train_transformer_classifier.py
```

Expected result: `artifacts/classifiers/transformer/` contains model weights,
tokenizer files, `model_card.json`, `metrics.json`, training data hash, artifact
SHA-256, architecture name, hyperparameters, freeze policy, training run ID, run
logger backend, training plots, MinIO artifact or manifest reference, and final
metrics.

## Upload Classifier Artifact Manifest

Run:

```bash
python scripts/upload_classifier_artifact_manifest.py
```

Expected result: the selected classifier artifact or manifest is stored in
MinIO for final review, and the model card or safe artifact metadata records the
MinIO reference.

## Run The LLM Baseline

Run in fake-provider test mode when real credentials are unavailable:

```bash
python scripts/run_llm_classifier_baseline.py
```

Expected result: LLM baseline predictions, latency, and cost shape are written
under `artifacts/classifiers/llm_baseline/`. Real-provider runs record cost where
applicable.

## Compare Classifiers

Run:

```bash
python scripts/evaluate_classifiers.py
```

Expected result: `evals/classifier_eval_report.json` compares completed
approaches on the same test split using accuracy, macro-F1, per-class F1,
confusion matrix, latency, and cost where applicable.

## Validate The Golden Set

Verify `evals/classification_golden_set.jsonl` contains exactly 25 examples and
at least one example per project label.

Expected result: golden set validation passes and can be reused by future CI or
regression checks.

## Validate The Transformer Artifact

Check the artifact hash, run-log metadata, plot references, and MinIO reference
against `model_card.json`.

Expected result: the computed artifact SHA-256 matches the model card. A modified
artifact fails validation and is not deployable. Missing run-log, plot, or MinIO
metadata keeps the artifact out of final-review/deployable status.

## Serve Classifier Predictions

Start the model server with a valid classifier artifact, then call the classifier
endpoint with issue title/body/comments text.

Expected result: the endpoint returns a typed label from `bug`, `feature`,
`docs`, or `question`, optional confidence, and model version.

Start the model server without a valid classifier artifact.

Expected result: the endpoint returns a structured unavailable-model error and no
stack trace.

## Update Decisions

Update `DECISIONS.md` with:

- classical baseline metrics
- transformer metrics and artifact hash
- transformer training run logger backend, run ID, training plots, and MinIO
  artifact reference
- LLM baseline metrics, latency, and cost where applicable
- selected classifier approach and rationale
- known limitations and rejected alternatives

Expected result: reviewer can verify the deployment choice is evidence-based.
