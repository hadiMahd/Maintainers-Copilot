## Runtime Functional Stack Plan

### Scope

This branch is for cross-phase runtime integration hardening across the existing
Phase 5, Phase 7, and Phase 8 implementation. It is not a new product phase.

The goal is to make the live Docker stack function end to end without fake
runtime clients in non-test execution paths.

### Objectives

1. Make the model server part of the functional Docker stack.
2. Wire backend-to-model-server communication over Docker service DNS, not
   container-local `localhost`.
3. Remove fake runtime RAG behavior and replace it with a real chat RAG path.
4. Replace placeholder long-term memory embeddings in runtime with a real
   embedding implementation.
5. Keep fake clients available only for tests and explicitly test-only seams.

### Runtime Acceptance Criteria

The branch is not done until all of the following are true in a live Docker
stack:

1. `backend` is healthy.
2. `model_server` is healthy.
3. `streamlit` is healthy.
4. Login works through the UI and directly against the backend.
5. Plain Azure-backed chat responds successfully.
6. `write_memory` succeeds through chat and persists/audits correctly.
7. `classify_issue` works against the live model server.
8. `extract_entities` works against the live model server.
9. `summarize_issue` works against the live model server.
10. `answer_project_question` uses a real retrieval/generation path, not a fake
    canned response.

### Constraints

1. Do not hardcode secrets.
2. Preserve existing route/service/repository/infra boundaries.
3. Keep tests free to use fake seams.
4. Non-test runtime must fail clearly rather than silently falling back to fake
   behavior.
5. Reuse existing Phase 5/6/7/8 services and repositories where possible.

### Primary Files

- `app/core/lifespan.py`
- `app/infra/llm_adapter.py`
- `app/infra/rag_tool_client.py`
- `app/infra/memory_embedding_client.py`
- `app/infra/model_server_tools.py`
- `app/services/tool_execution_service.py`
- `app/services/rag_*.py`
- `app/repositories/rag_*.py`
- `model_server/main.py`
- `model_server/Dockerfile`
- `docker-compose.yml`
- `docs/runbook.md`

### Validation Expectations

The implementation agent should:

1. run focused tests for changed areas,
2. rebuild the live Docker stack,
3. verify the live endpoints and UI behavior directly,
4. report which runtime fake paths were removed or replaced.
