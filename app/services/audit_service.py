"""Audit service.

Structured logging: propagate ``request_id`` from middleware and generate
per-operation ``trace_id``.  Audit metadata must be bounded, redacted,
and free of raw passwords, tokens, signing keys, or memory content.
"""

import uuid

import structlog


_log = structlog.get_logger


def _trace_ids(request_id: str | None = None) -> tuple[str, str]:
    rid = request_id or "unknown"
    tid = uuid.uuid4().hex[:12]
    return rid, tid
