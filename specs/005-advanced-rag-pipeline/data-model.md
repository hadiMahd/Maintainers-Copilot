# Data Model: Advanced RAG Pipeline

## RAG Source Document

**Purpose**: Documentation source available for RAG ingestion.

**Fields**:
- `source_id`: stable source identifier.
- `source_type`: `docs`.
- `source_path`: project-relative document path.
- `source_url`: optional external URL.
- `title`: document title.
- `updated_at`: source update timestamp when available.
- `content`: source text.
- `content_hash`: hash of normalized source content.

**Validation Rules**:
- `source_path`, `title`, and normalized content are required.
- Empty or unsupported documents are reported and skipped.
- Re-running ingestion with unchanged content produces the same `content_hash`.

## Resolved Issue Answer Source

**Purpose**: Held-out resolved issue content with maintainer answer evidence.

**Fields**:
- `source_id`: stable source identifier.
- `source_type`: `issue`.
- `issue_number`: source issue number.
- `source_url`: issue URL.
- `title`: issue title.
- `labels`: issue labels.
- `created_at`: issue creation timestamp.
- `updated_at`: issue update or close timestamp.
- `question_context`: issue problem statement and relevant discussion.
- `maintainer_answer`: maintainer-authored or reviewer-approved answer text.
- `content_hash`: hash of normalized answerable content.

**Validation Rules**:
- Issue-answer sources must come from held-out RAG/eval data and must not overlap
  classifier training records.
- Sources without a clear maintainer answer are excluded or marked unusable for
  answer evaluation.
- Real secrets and full raw issue payloads are not logged during ingestion.

## RAG Chunk

**Purpose**: Searchable unit produced from docs or issue-answer sources.

**Fields**:
- `chunk_id`: stable chunk identifier.
- `parent_id`: stable parent-document identifier linking child chunks back to
  the original document or issue-answer source.
- `source_type`: `docs` or `issue`.
- `source_path`: document path when source type is `docs`.
- `issue_number`: issue number when source type is `issue`.
- `source_url`: source URL.
- `title`: source title.
- `labels`: labels for issue chunks, empty list for docs when unavailable.
- `created_at`: source creation timestamp when available.
- `updated_at`: source update timestamp when available.
- `chunk_index`: deterministic index within source.
- `content`: chunk text.
- `content_hash`: hash of normalized chunk content.
- `token_count`: approximate token count.
- `metadata`: safe additional metadata such as heading path or answer marker.

**Validation Rules**:
- Required metadata from the spec must be present on every stored chunk.
- `parent_id` is required on every stored child chunk and must reference the
  parent-document retriever source record.
- `chunk_id` is stable for unchanged source, chunking policy, and chunk index.
- `content_hash` changes when normalized chunk content changes.
- `token_count` must be positive and within the configured chunking limits.
- Chunk content must not be logged wholesale.

## RAG Embedding

**Purpose**: Dense vector representation for one chunk and one embedding
candidate.

**Fields**:
- `embedding_id`: stable embedding identifier.
- `chunk_id`: associated chunk.
- `content_hash`: chunk content hash at embedding time.
- `embedding_model`: embedding candidate name/version.
- `embedding_dim`: vector dimension.
- `vector`: embedding vector stored in the retrieval store.
- `created_at`: embedding creation timestamp.

**Validation Rules**:
- One embedding may exist per `content_hash` and `embedding_model`.
- Changed chunk content requires a new embedding.
- Duplicate embeddings for unchanged content and model are skipped on rerun.
- Embedding records must not contain provider credentials.

## Sparse Search Record

**Purpose**: Sparse retrieval representation for chunk text and metadata.

**Fields**:
- `chunk_id`: associated chunk.
- `search_text`: normalized searchable text.
- `title_terms`: title or heading terms.
- `metadata_terms`: safe labels, paths, package names, or error codes.
- `updated_at`: last sparse-index update timestamp.

**Validation Rules**:
- Sparse search records are updated when chunk content or searchable metadata
  changes.
- Search text must be deterministic for unchanged chunks.

## Retrieval Query

**Purpose**: Maintainer question and retrieval controls.

**Fields**:
- `query`: maintainer question.
- `metadata_filters`: optional source type, labels, source path, issue number,
  and time bounds.
- `retrieval_mode`: `sparse`, `dense`, or `hybrid`.
- `embedding_model`: selected dense candidate for dense/hybrid modes.
- `query_transformation_enabled`: boolean.
- `reranking_enabled`: boolean.
- `top_k`: requested final result count.
- `candidate_k`: candidate count before reranking.

**Validation Rules**:
- Query text must be non-empty.
- Metadata filters must use known metadata fields.
- Query transformation can be enabled or disabled per evaluation run.
- `candidate_k` must be greater than or equal to `top_k`.

## Retrieval Result

**Purpose**: One scored retrieval result returned to generation or evaluation.

**Fields**:
- `chunk_id`: retrieved chunk.
- `rank`: final rank.
- `content_preview`: bounded preview or chunk reference.
- `metadata`: required chunk metadata.
- `sparse_score`: optional sparse score.
- `dense_score`: optional dense score.
- `hybrid_score`: optional combined score.
- `rerank_score`: optional cross-encoder score.
- `final_score`: score used for final ranking.

**Validation Rules**:
- Every result must include rank, final score, chunk reference, and complete
  required metadata.
- Score fields must be present according to retrieval/reranking mode.
- Ordering is deterministic for score ties.

## Grounded Answer

**Purpose**: Answer generated from retrieved evidence.

**Fields**:
- `question`: original maintainer question.
- `answer`: grounded answer text.
- `supporting_chunks`: chunk IDs or source references used as evidence.
- `insufficient_evidence`: boolean.
- `limitations`: optional safe limitations or conflicts.
- `generation_latency_ms`: generation latency.

**Validation Rules**:
- Answerable outputs cite or identify supporting chunks.
- Unanswerable outputs set `insufficient_evidence` and avoid unsupported claims.
- Full prompts and retrieved chunk payloads are not logged.

## RAG Golden Example

**Purpose**: One evaluation example for retrieval and generation.

**Fields**:
- `id`: stable example identifier.
- `question`: maintainer question.
- `expected_relevant_chunk_ids`: expected supporting chunks or source IDs.
- `expected_answer_points`: answer facts expected from evidence.
- `source_type`: expected source family, such as docs or issue.
- `metadata_filters`: optional filters for the example.
- `hand_labeled`: whether the example is part of the five hand-labeled judge
  disagreement checks.
- `notes`: reviewer notes.

**Validation Rules**:
- Exactly 25 examples are required.
- Both documentation-backed and issue-answer-backed examples must be present.
- At least five examples are marked for hand-labeled judge disagreement notes.
- Expected evidence must reference held-out or documentation sources, not
  classifier training records.

## RAG Evaluation Run

**Purpose**: Metrics and artifacts for one pipeline run.

**Fields**:
- `run_id`: stable run identifier.
- `mode`: `baseline` or `advanced`.
- `chunking_strategy`: strategy name/version.
- `embedding_model`: embedding candidate.
- `retrieval_mode`: retrieval mode.
- `hybrid_weighting`: sparse/dense weighting when applicable.
- `query_transformation_enabled`: boolean.
- `reranking_enabled`: boolean.
- `metrics`: retrieval, generation, and latency metrics.
- `judge_id`: stable judge identifier for required CI metrics, such as
  `token-overlap-f1-v1`.
- `optional_ragas_metrics`: optional RAGAS-style metric values when available.
- `limitations`: known run limitations.

**Validation Rules**:
- Baseline and advanced runs must use the same golden set.
- Baseline uses fixed-size chunking plus pure dense retrieval.
- Advanced run records all enabled retrieval controls.
- Required CI runs record the frozen local/mockable `judge_id` and do not
  require paid provider credentials.

## RAG Evaluation Report

**Purpose**: Reviewable comparison of baseline and advanced RAG behavior.

**Fields**:
- `golden_set_hash`: hash of the 25-example golden set.
- `baseline`: baseline evaluation run.
- `advanced`: advanced evaluation run.
- `embedding_comparison`: metrics for at least two embedding candidates.
- `hit_at_5`: retrieval metric by run.
- `mrr_at_10`: retrieval metric by run.
- `faithfulness`: generation metric by run.
- `answer_relevancy`: generation metric by run.
- `retrieval_latency`: latency summary by run.
- `generation_latency`: latency summary by run.
- `reranking_impact`: ranking changes and metric impact.
- `judge_disagreement_notes`: notes for five hand-labeled examples.
- `judge_id`: frozen local/mockable CI judge identity.
- `optional_ragas_metrics`: optional RAGAS-style metrics, stored separately from
  required CI judge metrics.
- `generated_at`: report timestamp.
- `limitations`: known limitations.

**Validation Rules**:
- Required metrics must be present for baseline and advanced runs.
- Advanced hit@5 and MRR@10 must exceed baseline values before the phase is
  considered complete.
- Report JSON must be schema-valid and safe to commit.
- Required generation metrics identify the frozen CI judge used.

## Retrieved Chunk Snapshot

**Purpose**: Redacted bounded record of RAG retrieval evidence for recent
conversations.

**Fields**:
- `snapshot_id`: stable snapshot identifier.
- `conversation_id`: associated conversation.
- `message_id`: user message that triggered retrieval.
- `trace_id`: trace identifier when available.
- `query_hash`: hash of the redacted query.
- `retrieved_chunks`: bounded list of chunk IDs, source metadata, scores, and
  redacted previews.
- `created_at`: snapshot timestamp.
- `retention_rank`: ordering value used to keep only the last 50 conversations.

**Validation Rules**:
- Stored previews must be redacted and bounded.
- Full raw chunks, full prompts, and raw secrets are not stored.
- Retention keeps only the configured last 50 conversations.
- Snapshot creation is callable by the chat phase without rerunning ingestion or
  embedding.

## RAG Decision Record

**Purpose**: `DECISIONS.md` section documenting selected RAG choices.

**Fields**:
- `selected_embedding_model`: chosen embedding candidate and rationale.
- `selected_chunking_strategy`: chosen non-naive chunking policy.
- `selected_retrieval_weighting`: hybrid sparse/dense weights.
- `reranking_impact`: measured reranking result.
- `generation_behavior`: grounded answer and insufficiency policy.
- `metrics_summary`: required metrics from the eval report.
- `alternatives_considered`: rejected choices and rationale.
- `limitations`: known risks and bootcamp constraints.

**Validation Rules**:
- Must cite the eval report.
- Must include numbers for embedding, chunking, weighting, and reranking.
- Must be updated before the phase is considered complete.
