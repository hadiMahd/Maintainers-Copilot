# Research: NER and Summarization Tools

## Decision: Use spaCy `EntityRuler` with custom patterns for code-shaped NER

**Rationale**: The supported entity types are structured, code-shaped, and
reviewable. spaCy `EntityRuler` gives deterministic pattern matching, stable
entity spans, and one in-process pipeline without any external dependency or
training loop. That matches the phase requirement for explainable extraction and
keeps runtime predictable.

**Alternatives considered**:
- Plain regex-only helpers: rejected because the updated spec explicitly chose a
  spaCy `EntityRuler` pipeline and because spaCy gives cleaner span handling and
  pattern organization.
- Custom NER training: rejected because the phase explicitly forbids overbuilt
  NER training.
- General pretrained NER model: rejected because generic entity models do not
  reliably cover file paths, error codes, stack-trace markers, and command
  snippets.

## Decision: Keep confidence optional for deterministic entities

**Rationale**: `EntityRuler` matches are deterministic rather than probabilistic.
Returning fabricated confidence values would make the response less honest.
Confidence remains optional so future phases can add it if they adopt a model
that provides a real score.

**Alternatives considered**:
- Always return `1.0`: rejected because pattern matches are not calibrated model
  probabilities.
- Add heuristic confidence scoring now: rejected because the phase does not need
  invented scoring semantics.

## Decision: Return best-effort source spans from the spaCy match offsets

**Rationale**: Callers need to map entities back to title, body, or comment
text. Using source field plus start/end offsets is enough for Phase 4 and stays
testable. Comment offsets remain relative to the original comment string.

**Alternatives considered**:
- Omit spans entirely: rejected because the contract requires spans when
  practical.
- Use one global offset across concatenated issue text: rejected because it adds
  caller-side remapping complexity without user value.

## Decision: Enforce a hard 8,000-character combined input limit

**Rationale**: The spec explicitly set 8,000 total characters across title,
body, and comments. A hard validation boundary is simpler and safer than
truncating or chunking content because it preserves deterministic behavior and
avoids partial summaries or misleading NER output.

**Alternatives considered**:
- Silent truncation: rejected because callers would not know that output was
  incomplete.
- Automatic chunking: rejected because chunk orchestration belongs to later
  chatbot or RAG phases, not this tool phase.

## Decision: Use Azure OpenAI via LangChain `AzureChatOpenAI` for summarization

**Rationale**: Phase 3 already introduced Azure OpenAI plus Vault-resolved
credentials and LangSmith tracing. Reusing that provider stack avoids a second
LLM integration style, keeps secret handling consistent, and fits the clarified
spec.

**Alternatives considered**:
- Direct `httpx` calls to Azure OpenAI: rejected because LangChain is the
  clarified stack and gives a cleaner fake-adapter testing seam.
- Local pretrained summarizer: rejected because the phase now explicitly prefers
  Azure OpenAI via LangChain and does not require an additional local model
  runtime.

## Decision: Use a fake LangChain summarization adapter in automated tests

**Rationale**: Tests must run without real Azure credentials and without paid
API calls. A fake adapter keeps the service contract deterministic while still
exercising service logic, timeout mapping, and response shaping.

**Alternatives considered**:
- Skip summarization tests unless Azure credentials exist: rejected because it
  would make Phase 4 non-reproducible.
- Record/replay provider transcripts: rejected because it adds brittle fixtures
  and still requires credential management.

## Decision: Return structured tool errors only when summarization is unavailable or times out

**Rationale**: The clarified spec explicitly forbids fallback or stub summary
content when Azure OpenAI is unavailable or exceeds the 15-second timeout.
Returning only a structured tool error keeps degradation explicit and prevents
callers from treating synthetic text as a real model answer.

**Alternatives considered**:
- Deterministic fallback summary: rejected because the spec now forbids fallback
  summary content.
- Empty successful response with warning fields: rejected because it hides a
  real tool failure behind a 200 response.

## Decision: Bound Azure summarization with a 15-second timeout

**Rationale**: The spec defines 15 seconds as the external summarization limit.
Making the timeout explicit in the adapter preserves async safety and gives
predictable failure handling.

**Alternatives considered**:
- No explicit timeout: rejected because it violates the constitution’s async
  safety rule.
- Shorter timeout such as 5 seconds: rejected because the requirement is
  already clarified at 15 seconds.

## Decision: Log only redacted, bounded issue-analysis metadata

**Rationale**: Issue threads may contain stack traces, URLs, commands, and
secret-like values. The service should log request ID, tool name, lengths,
entity count, and safe status fields only, while relying on the shared
redaction layer for any unavoidable textual metadata.

**Alternatives considered**:
- Full payload logging for debugging: rejected because it violates the
  constitution and the acceptance criteria.
- No logging at all: rejected because the model server still needs diagnosable
  request and failure traces.
