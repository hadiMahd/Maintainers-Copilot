"""RAG domain models and exceptions.

Models only. Orchestration lives in ``app/services/``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

RAGSourceType = Literal["docs", "issue"]
RetrievalMode = Literal["sparse", "dense", "hybrid"]
EmbeddingModelName = Literal["all-MiniLM-L6-v2", "text-embedding-3-small", "fake-embedding"]


# -- Domain exceptions ---------------------------------------------------------

class RAGDomainError(Exception):
    """Base RAG domain error."""

    error_code: str = "RAG_DOMAIN_ERROR"

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class RAGRetrievalError(RAGDomainError):
    """Retrieval failed — unavailable store, invalid query, or timeout."""

    error_code = "RAG_RETRIEVAL_ERROR"


class RAGGenerationError(RAGDomainError):
    """Generation failed — provider unavailable, timeout, or malformed output."""

    error_code = "RAG_GENERATION_ERROR"


class RAGInsufficientEvidenceError(RAGDomainError):
    """Retrieved evidence is insufficient to produce a grounded answer."""

    error_code = "RAG_INSUFFICIENT_EVIDENCE"


# -- Source entities -----------------------------------------------------------

class RAGSource(BaseModel):
    """Documentation or issue source available for RAG ingestion."""

    source_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    source_type: RAGSourceType
    source_path: str
    source_url: str | None = None
    title: str
    updated_at: datetime | None = None
    content: str
    content_hash: str


class ResolvedIssueAnswer(RAGSource):
    """Held-out resolved issue with maintainer answer."""

    source_type: RAGSourceType = "issue"
    issue_number: int | None = None
    labels: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    question_context: str | None = None
    maintainer_answer: str = ""


# -- Chunk entities ------------------------------------------------------------

class RAGChunk(BaseModel):
    """Searchable unit with parent-document linkage."""

    chunk_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    parent_id: str
    source_type: RAGSourceType
    source_path: str | None = None
    issue_number: int | None = None
    source_url: str | None = None
    title: str | None = None
    labels: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    chunk_index: int = 0
    content: str
    content_hash: str
    token_count: int = Field(ge=1)
    metadata: dict = Field(default_factory=dict)


# -- Embedding entities --------------------------------------------------------

class RAGEmbedding(BaseModel):
    """Dense vector for one chunk and one embedding model."""

    embedding_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    chunk_id: str
    content_hash: str
    embedding_model: EmbeddingModelName
    embedding_dim: int = Field(ge=1)
    vector: list[float] = Field(default_factory=list)
    created_at: datetime | None = None


class SparseSearchRecord(BaseModel):
    """Sparse retrieval representation for one chunk."""

    chunk_id: str
    search_text: str
    title_terms: str = ""
    metadata_terms: str = ""
    updated_at: datetime | None = None


# -- Retrieval entities --------------------------------------------------------

class RetrievalQuery(BaseModel):
    """Maintainer question with retrieval controls."""

    query: str = Field(min_length=1)
    metadata_filters: dict = Field(default_factory=dict)
    retrieval_mode: RetrievalMode = "hybrid"
    embedding_model: EmbeddingModelName | None = None
    query_transformation_enabled: bool = False
    reranking_enabled: bool = False
    top_k: int = Field(default=5, ge=1, le=50)
    candidate_k: int = Field(default=20, ge=1, le=100)


class RetrievalResult(BaseModel):
    """One scored retrieved chunk."""

    rank: int = Field(ge=1)
    final_score: float
    chunk: RAGChunk
    content_preview: str = ""
    sparse_score: float | None = None
    dense_score: float | None = None
    rerank_score: float | None = None
    retrieval_mode: RetrievalMode = "hybrid"


class RetrievalResultSet(BaseModel):
    """Ordered retrieval results with metadata."""

    results: list[RetrievalResult]
    retrieval_mode: RetrievalMode = "hybrid"
    query_transformation_applied: bool = False
    reranking_applied: bool = False
    retrieval_latency_ms: float | None = None
    explanation: str | None = None
    request_id: str | None = None


# -- Generation entities -------------------------------------------------------

class GroundedAnswer(BaseModel):
    """Maintainer-facing answer grounded in retrieved evidence."""

    answer: str = Field(min_length=1)
    supporting_chunk_ids: list[str] = Field(default_factory=list)
    insufficient_evidence: bool = False
    limitations: list[str] | None = None
    generation_latency_ms: float | None = None
    request_id: str | None = None


# -- Evaluation entities -------------------------------------------------------

class EvalMetrics(BaseModel):
    """Retrieval and generation metrics for one run mode."""

    hit_at_5: float = 0.0
    mrr_at_10: float = 0.0
    faithfulness: float | None = None
    answer_relevancy: float | None = None
    retrieval_latency_ms_p50: float | None = None
    retrieval_latency_ms_p95: float | None = None
    generation_latency_ms_p50: float | None = None
    generation_latency_ms_p95: float | None = None


class EvalRun(BaseModel):
    """One evaluation run."""

    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    mode: Literal["baseline", "advanced"]
    metrics: EvalMetrics = Field(default_factory=EvalMetrics)
    embedding_model: EmbeddingModelName | None = None
    retrieval_mode: RetrievalMode | None = None
    reranking_enabled: bool = False
    query_transformation_enabled: bool = False
    examples_completed: int = 0
    judge_id: str | None = None
    disagreement_notes: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


class EvalReport(BaseModel):
    """Comparison report between baseline and advanced RAG."""

    report_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    baseline: EvalRun
    advanced: EvalRun
    advanced_beats_baseline: bool = False
    embedding_comparison: dict = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


# -- Snapshot entities ---------------------------------------------------------

class SnapshotRecord(BaseModel):
    """Redacted retrieved-chunk snapshot for one conversation message."""

    snapshot_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    conversation_id: str
    message_id: str
    trace_id: str | None = None
    query: str = ""
    chunk_ids: list[str] = Field(default_factory=list)
    scores: list[float] = Field(default_factory=list)
    metadata_preview: dict = Field(default_factory=dict)
    created_at: datetime | None = None


__all__ = [
    "RAGDomainError",
    "RAGRetrievalError",
    "RAGGenerationError",
    "RAGInsufficientEvidenceError",
    "RAGSource",
    "ResolvedIssueAnswer",
    "RAGChunk",
    "RAGEmbedding",
    "SparseSearchRecord",
    "RetrievalQuery",
    "RetrievalResult",
    "RetrievalResultSet",
    "GroundedAnswer",
    "EvalMetrics",
    "EvalRun",
    "EvalReport",
    "SnapshotRecord",
    "RAGSourceType",
    "RetrievalMode",
    "EmbeddingModelName",
]
