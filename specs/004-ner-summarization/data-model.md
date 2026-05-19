# Data Model: NER and Summarization Tools

## Issue Text Input

**Purpose**: Shared request payload accepted by `/ner` and `/summarize`.

**Fields**:
- `title`: issue title text.
- `body`: issue body text.
- `comments`: ordered list of issue comment text.

**Derived Fields**:
- `combined_characters`: total characters across `title`, `body`, and every
  comment string.

**Validation Rules**:
- At least one of `title`, `body`, or `comments` must contain non-whitespace
  text.
- Empty or whitespace-only comments are ignored deterministically by services.
- `combined_characters` must not exceed `8_000`.
- Raw request text must never be logged wholesale.

## Entity Type

**Purpose**: Stable category for supported code-shaped entities.

**Values**:
- `file_path`
- `function_name`
- `class_name`
- `package_name`
- `version_number`
- `error_code`
- `url`
- `stack_trace_marker`
- `environment_name`
- `command_snippet`

**Validation Rules**:
- Returned entity types must be one of the supported values.
- Matching priority and conflict behavior must be deterministic.

## Source Span

**Purpose**: Best-effort trace back to where an entity was found in the request.

**Fields**:
- `source_field`: `title`, `body`, or `comments`.
- `comment_index`: zero-based index when `source_field` is `comments`.
- `start`: zero-based start character offset within the source field.
- `end`: exclusive end character offset within the source field.

**Validation Rules**:
- `start >= 0`.
- `end > start`.
- `comment_index` is present only for comment spans.
- The span is omitted when the pipeline cannot provide a reliable mapping.

## Extracted Entity

**Purpose**: One detected entity returned by the NER tool.

**Fields**:
- `text`: matched entity text.
- `type`: supported entity type.
- `confidence`: optional score when the extraction method can justify it.
- `span`: optional source span.
- `source_field`: shorthand source location for callers that do not inspect the
  full span object.

**Validation Rules**:
- `text` must be non-empty after trimming.
- `type` must be supported.
- `confidence`, when present, must be between `0` and `1`.
- Duplicate entities with the same `text`, `type`, and `span` are collapsed.

## NER Response

**Purpose**: Successful `/ner` response.

**Fields**:
- `entities`: ordered list of extracted entities.
- `warnings`: optional safe warnings about omitted spans or normalized input.
- `request_id`: request identifier when available.

**Validation Rules**:
- `entities` is always present, even when empty.
- Order is deterministic by source order and pipeline match order.
- Warnings must not contain raw issue payload text.

## Summarization Request

**Purpose**: `/summarize` request payload.

**Fields**:
- All `Issue Text Input` fields.
- `max_summary_sentences`: optional caller hint for concise output.

**Validation Rules**:
- Inherits `Issue Text Input` validation rules.
- `max_summary_sentences`, when present, must stay within documented bounds.
- Oversized input returns a structured validation error; no truncation or
  chunking occurs in Phase 4.

## Issue Summary

**Purpose**: Successful `/summarize` response.

**Fields**:
- `summary`: concise issue summary.
- `key_facts`: list of maintainer-relevant facts.
- `unresolved_questions`: list of unanswered or uncertain questions.
- `suggested_next_step`: optional suggested maintainer action.
- `limitations`: optional safe notes about unavailable fields or bounded output.
- `request_id`: request identifier when available.

**Validation Rules**:
- `summary` is required for a successful response.
- `key_facts` and `unresolved_questions` are always lists.
- `suggested_next_step` may be omitted or null when unsupported.
- No successful response may contain provider secrets or raw exception text.

## Tool Error

**Purpose**: Stable failure shape for both tools.

**Fields**:
- `code`: stable machine-readable error code.
- `message`: safe human-readable failure message.
- `request_id`: request identifier when available.
- `details`: optional safe metadata such as input length or timeout seconds.

**Validation Rules**:
- Details must never include full raw title/body/comments, prompts, credentials,
  provider responses, or stack traces.
- Known failure cases map to stable codes:
  - `invalid_tool_input`
  - `ner_extraction_failed`
  - `summarizer_unavailable`
  - `summarizer_timeout`
  - `tool_execution_failed`
  - `internal_error`

## NER Adapter

**Purpose**: Deterministic extraction pipeline owned by infra.

**Fields**:
- `pipeline_name`: internal pipeline identifier.
- `configured`: whether the `EntityRuler` pipeline was initialized at startup.
- `supported_entity_types`: ordered list of supported entity types.

**Validation Rules**:
- The adapter performs no external network calls.
- Pattern definitions are deterministic and testable.
- Startup failures map to structured tool errors rather than crashing requests.

## Summarization Adapter

**Purpose**: Async LangChain wrapper used by the summarization service.

**Fields**:
- `provider_backend`: `azure_openai`.
- `tracing_backend`: `langsmith` when configured, otherwise null.
- `timeout_seconds`: configured timeout, fixed at `15`.
- `configured`: whether runtime credentials and model settings are available.
- `supports_next_step`: whether the adapter can supply maintainer next-step text.

**Validation Rules**:
- Runtime secrets resolve from Vault bootstrap settings or a test fake.
- Adapter configuration metadata must stay redacted in logs and traces.
- Timeout or availability failure returns a structured tool error only; no
  fallback summary content is produced.
