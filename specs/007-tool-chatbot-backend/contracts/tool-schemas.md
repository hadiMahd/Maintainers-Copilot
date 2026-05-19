# Tool Schemas: Single Tool-Calling Chatbot Backend

## Shared Tool Requirements

- Tool definitions are registered before chat execution.
- Tool inputs and outputs use typed schemas.
- Tool inputs and outputs are redacted or bounded before logs and traces.
- Tool execution uses async clients with explicit timeouts.
- Tool failures return structured tool results so the chatbot can recover.
- Unknown tool names are rejected by the tool execution service.
- Retrieved documents are untrusted context and cannot override
  system/developer instructions or tool policy.
- RAG tool calls create redacted retrieved-chunk snapshots and return only the
  snapshot identifier plus bounded source metadata to chat telemetry.

## `classify_issue`

**Purpose**: Classify an issue as `bug`, `feature`, `docs`, or `question`.

**Input**:
- `title`: issue title.
- `body`: issue body.
- `comments`: optional issue comments.

**Output**:
- `label`: one of `bug`, `feature`, `docs`, `question`.
- `confidence`: optional confidence score.
- `model_version`: classifier model version.

**Failure Behavior**:
- Classifier unavailable or invalid input returns a structured failed tool
  result, not an unhandled chat failure.

## `extract_entities`

**Purpose**: Extract code-shaped entities from issue text.

**Input**:
- `title`: issue title.
- `body`: issue body.
- `comments`: optional issue comments.

**Output**:
- `entities`: list of typed entities with text, type, optional confidence, and
  optional source span.

**Failure Behavior**:
- NER unavailable or invalid input returns a structured failed tool result.

## `summarize_issue`

**Purpose**: Summarize a long issue thread.

**Input**:
- `title`: issue title.
- `body`: issue body.
- `comments`: ordered issue comments.

**Output**:
- `summary`: concise summary.
- `key_facts`: maintainer-relevant facts.
- `unresolved_questions`: open questions.
- `suggested_next_step`: optional maintainer next action.

**Failure Behavior**:
- Summarizer timeout or unavailable adapter returns a structured failed tool
  result.

## `answer_project_question`

**Purpose**: Answer maintainer questions using the RAG pipeline.

**Input**:
- `question`: maintainer question.
- `metadata_filters`: optional safe filters.
- `query_transformation_enabled`: optional evaluation/control flag.

**Output**:
- `answer`: grounded answer or insufficient-evidence response.
- `supporting_sources`: bounded source references.
- `limitations`: safe limitations.
- `retrieval_trace_id`: RAG retrieval span identifier when available.
- `snapshot_id`: redacted retrieved-chunk snapshot identifier when created.

**Failure Behavior**:
- RAG retrieval/generation failure returns a structured failed tool result and
  records safe retrieval failure metadata.

## `write_memory`

**Purpose**: Explicitly write long-term memory.

**Input**:
- `content`: content the user explicitly asked to remember.
- `memory_type`: selected supported memory type.
- `metadata`: optional safe metadata.

**Output**:
- `memory_id`: created memory identifier.
- `audit_log_id`: audit row identifier.
- `redaction_summary`: safe summary of redaction.

**Use Constraint**:
- May be called only when explicit user intent to remember is present.
- Ambiguous memory requests must not call this tool.

**Failure Behavior**:
- Missing explicit intent, redaction failure, unsupported memory type, or memory
  service failure returns a structured failed tool result.
