# Service Contract: Advanced RAG Pipeline

## Retrieval Service

**Purpose**: Retrieve scored chunks for a maintainer question.

**Input**:
- `query`: non-empty maintainer question.
- `metadata_filters`: optional filters for source type, source path, issue
  number, labels, and timestamp bounds.
- `retrieval_mode`: `sparse`, `dense`, or `hybrid`.
- `embedding_model`: selected embedding model for dense or hybrid retrieval.
- `query_transformation_enabled`: boolean.
- `reranking_enabled`: boolean.
- `top_k`: final number of chunks.
- `candidate_k`: number of candidates before reranking.

**Output**:
- Ordered retrieval results with rank, final score, chunk reference, content
  preview, required metadata, and sparse/dense/hybrid/rerank scores when
  available.

**Behavior Contract**:
- Uses async database access when called from an API-facing path.
- Applies metadata filters before final result return.
- Query transformation can be toggled on or off per call/eval run.
- Hybrid retrieval combines normalized sparse and dense scores with configured
  weights.
- Reranking runs only over top-k candidates and must produce deterministic
  ordering for ties.
- Empty filtered result sets return an empty list and safe explanation, not
  unrelated chunks.

**Failure Behavior**:
- Invalid filters, missing embedding model, unavailable retrieval store, and
  timeout failures return structured domain errors with safe details.

## Grounded Generation Service

**Purpose**: Generate a maintainer-facing answer from retrieved evidence.

**Input**:
- Original question.
- Ordered retrieval results.
- Generation configuration and timeout.

**Output**:
- Answer text.
- Supporting chunk references.
- `insufficient_evidence` flag.
- Limitations or conflict notes.
- Generation latency.

**Behavior Contract**:
- Uses only retrieved evidence for answer claims.
- Identifies supporting chunks for answerable outputs.
- Returns insufficient-evidence behavior when retrieved chunks do not support an
  answer.
- Avoids logging full prompts, source documents, issue bodies, or generated
  provider payloads.

**Failure Behavior**:
- Provider unavailable, provider timeout, malformed provider output, and empty
  evidence produce structured errors or documented fallback behavior.

## Evaluation Service

**Purpose**: Compare baseline and advanced RAG behavior on the golden set.

**Input**:
- 25-example RAG golden set.
- Baseline retrieval/generation configuration.
- Advanced retrieval/generation configuration.
- Judge configuration for faithfulness and answer relevancy.

**Output**:
- Evaluation report with required retrieval metrics, generation metrics,
  latencies, embedding comparison, reranking impact, query transformation mode,
  frozen local/mockable CI judge identity, optional RAGAS-style metrics when
  available, judge disagreement notes, limitations, and run identifiers.

**Behavior Contract**:
- Baseline and advanced runs use the same golden examples.
- Baseline uses fixed-size chunking plus pure dense retrieval.
- Advanced run records non-naive chunking, sparse/dense hybrid weighting,
  metadata filters, query transformation mode, and reranking mode.
- Required CI generation metrics use the frozen local/mockable judge and do not
  depend on paid provider credentials.
- Optional RAGAS-style metrics are recorded separately and do not replace the CI
  judge gate.
- Eval gates fail when advanced hit@5 or MRR@10 does not exceed baseline.

**Failure Behavior**:
- Missing examples, invalid expected chunks, metric calculation failures, judge
  provider failures, and failed eval gates produce safe structured failures.

## Retrieved-Chunk Snapshot Service

**Purpose**: Store redacted bounded retrieval evidence for recent conversations
after a RAG tool call.

**Input**:
- Conversation identifier.
- User message identifier.
- Trace identifier when available.
- Original or redacted query.
- Retrieval results with chunk IDs, scores, metadata, and bounded previews.
- Retention limit for the last N conversations.

**Output**:
- Snapshot identifier and stored metadata summary.

**Behavior Contract**:
- Redacts queries and previews before storage.
- Stores chunk IDs, scores, and safe metadata instead of full raw chunks.
- Enforces last-N conversation retention deterministically.
- Can be called by Phase 7 chat after RAG retrieval without rerunning ingestion,
  embedding, or generation.

**Failure Behavior**:
- Redaction failure, storage failure, or retention cleanup failure returns a
  structured error and must not leak raw retrieved content.
