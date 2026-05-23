"""Thin authenticated SSE chat route."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

import app.infra.database as db_mod
from app.api.dependencies.auth import get_current_user
from app.core.config import AppSettings
from app.domain.auth import AuthContext
from app.domain.chat import ChatLimits, ChatRequest
from app.infra.conversation_state_adapter import ConversationStateAdapter
from app.infra.llm_adapter import FakeLLMAdapter
from app.infra.memory_embedding_client import resolve_memory_embedding_client
from app.infra.memory_tool_client import FakeMemoryToolClient, MemoryToolClient
from app.infra.model_server_tools import FakeModelServerTools
from app.infra.prompt_registry import PromptRegistry
from app.infra.rag_tool_client import FakeRAGToolClient
from app.infra.tracing import FakeTraceAdapter
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.memory_repository import MemoryRepository
from app.repositories.rag_snapshot_repository import RAGSnapshotRepository
from app.services.chat_rag_snapshot_coordinator import ChatRAGSnapshotCoordinator
from app.services.chat_tracing_service import ChatTracingService
from app.services.chatbot_graph_service import ChatbotGraphService
from app.services.chatbot_service import ChatbotService
from app.services.conversation_state_service import ConversationStateService
from app.services.long_term_memory_service import LongTermMemoryService
from app.services.rag_snapshot_service import RAGSnapshotService
from app.services.tool_execution_service import ToolExecutionService

router = APIRouter()


def _get_limits(settings: AppSettings) -> ChatLimits:
    return ChatLimits(
        request_size_limit_bytes=settings.chat_request_size_limit_bytes,
        context_size_limit_chars=settings.chat_context_size_limit_chars,
        max_tool_calls=settings.chat_max_tool_calls,
        recursion_limit=settings.chat_recursion_limit,
        total_timeout_seconds=settings.chat_total_timeout_seconds,
        per_tool_timeout_seconds=settings.chat_per_tool_timeout_seconds,
    )


def _get_prompt_registry(request: Request) -> PromptRegistry:
    registry = getattr(request.app.state, "prompt_registry", None)
    if registry is None:
        registry = PromptRegistry.from_settings(request.app.state.settings)
        request.app.state.prompt_registry = registry
    return registry


def _get_trace_service(request: Request) -> ChatTracingService:
    adapter = getattr(request.app.state, "chat_trace_adapter", None) or FakeTraceAdapter()
    return ChatTracingService(adapter)


def _get_conversation_state_service(request: Request) -> ConversationStateService:
    settings: AppSettings = request.app.state.settings
    adapter = getattr(request.app.state, "chat_conversation_state_adapter", None)
    if adapter is None:
        adapter = ConversationStateAdapter(request.app.state.redis)
        request.app.state.chat_conversation_state_adapter = adapter
    return ConversationStateService(
        adapter=adapter,
        ttl_seconds=settings.short_term_memory_ttl_seconds,
        context_size_limit_chars=settings.chat_context_size_limit_chars,
    )


def _get_memory_tool_client(request: Request):
    session_factory = getattr(request.app.state, "db_session_factory", db_mod.async_session_factory)
    if session_factory is None:
        return FakeMemoryToolClient()
    service = LongTermMemoryService(
        memory_repo=MemoryRepository,
        audit_repo=AuditLogRepository,
        embedding_client=resolve_memory_embedding_client(request.app.state.settings),
        session_factory=session_factory,
    )
    return MemoryToolClient(service)


def _get_rag_snapshot_coordinator(request: Request) -> ChatRAGSnapshotCoordinator:
    session_factory = getattr(request.app.state, "db_session_factory", db_mod.async_session_factory)

    if session_factory is None:

        class _FakeSnapshotService:
            async def store_snapshot(self, **kwargs):
                from app.domain.rag import SnapshotRecord

                return SnapshotRecord(
                    conversation_id=kwargs["conversation_id"],
                    message_id=kwargs["message_id"],
                    trace_id=kwargs.get("trace_id"),
                    query=kwargs["query"],
                    chunk_ids=[],
                    scores=[],
                )

        return ChatRAGSnapshotCoordinator(_FakeSnapshotService())

    class _SessionFactorySnapshotService:
        def __init__(self, factory, max_conversations: int) -> None:
            self._factory = factory
            self._max_conversations = max_conversations

        async def store_snapshot(self, **kwargs):
            async with self._factory() as session:
                service = RAGSnapshotService(
                    repo=RAGSnapshotRepository(session),
                    max_conversations=self._max_conversations,
                )
                stored = await service.store_snapshot(**kwargs)
                await session.commit()
                return stored

    snapshot_service = _SessionFactorySnapshotService(
        session_factory,
        request.app.state.settings.rag_snapshot_retention_conversations,
    )
    return ChatRAGSnapshotCoordinator(snapshot_service)


def _get_tool_execution_service(request: Request) -> ToolExecutionService:
    settings: AppSettings = request.app.state.settings
    model_server_tools = (
        getattr(request.app.state, "chat_model_server_tools", None) or FakeModelServerTools()
    )
    rag_tool_client = (
        getattr(request.app.state, "chat_rag_tool_client", None) or FakeRAGToolClient()
    )
    return ToolExecutionService(
        model_server_tools=model_server_tools,
        rag_tool_client=rag_tool_client,
        memory_tool_client=_get_memory_tool_client(request),
        rag_snapshot_coordinator=_get_rag_snapshot_coordinator(request),
        per_tool_timeout_seconds=settings.chat_per_tool_timeout_seconds,
    )


def _get_chatbot_graph_service(request: Request) -> ChatbotGraphService:
    llm_adapter = getattr(request.app.state, "chat_llm_adapter", None) or FakeLLMAdapter()
    return ChatbotGraphService(
        llm_adapter=llm_adapter,
        prompt_registry=_get_prompt_registry(request),
        tool_execution_service=_get_tool_execution_service(request),
        tracing_service=_get_trace_service(request),
    )


def _get_chatbot_service(request: Request) -> ChatbotService:
    settings: AppSettings = request.app.state.settings
    return ChatbotService(
        conversation_state_service=_get_conversation_state_service(request),
        chatbot_graph_service=_get_chatbot_graph_service(request),
        tracing_service=_get_trace_service(request),
        limits=_get_limits(settings),
    )


@router.post("/chat")
async def chat_with_maintainer_copilot(
    body: ChatRequest,
    request: Request,
    current_user: AuthContext = Depends(get_current_user),
) -> StreamingResponse:
    service = _get_chatbot_service(request)
    request_id = getattr(request.state, "request_id", "unknown")
    result = await service.execute_chat(
        user_id=current_user.user_id,
        body=body,
        request_id=request_id,
    )
    request.state.trace_id = result.trace_id
    return StreamingResponse(
        ChatbotService.format_sse(result),
        media_type="text/event-stream",
        headers={
            "X-Request-ID": request_id,
            **({"X-Trace-ID": result.trace_id} if result.trace_id else {}),
        },
    )
