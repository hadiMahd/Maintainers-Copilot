"""Widget public routes — config read, session issuance, chat.

Thin HTTP mapping — delegates to services for origin validation,
token issuance, and chat orchestration.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.domain.errors import WidgetEmbedError, WidgetSessionError
from app.domain.widget_config import PublicWidgetConfigRead, WidgetSessionToken
from app.services.widget_embed_service import WidgetEmbedService
from app.services.widget_session_service import WidgetSessionService

router = APIRouter(prefix="/public/widgets", tags=["widget-public"])


def _get_widget_config_service(request: Request):
    from app.repositories.widget_config_repository import WidgetConfigRepository
    from app.services.widget_config_service import WidgetConfigService
    import app.infra.database as db_mod
    return WidgetConfigService(
        widget_config_repo=WidgetConfigRepository,
        session_factory=db_mod.async_session_factory,
    )


def _get_widget_chat_service(request: Request):
    from app.services.widget_chat_service import WidgetChatService
    from app.services.chatbot_service import ChatbotService
    from app.services.conversation_state_service import ConversationStateService
    from app.services.chatbot_graph_service import ChatbotGraphService
    from app.services.chat_tracing_service import ChatTracingService
    from app.infra.conversation_state_adapter import ConversationStateAdapter
    from app.infra.llm_adapter import AzureChatLLMAdapter, FakeLLMAdapter
    from app.infra.prompt_registry import PromptRegistry
    from app.infra.tracing import FakeTraceAdapter
    from app.core.config import AppSettings

    settings = AppSettings()
    adapter = getattr(request.app.state, "chat_conversation_state_adapter", None)
    if adapter is None:
        adapter = ConversationStateAdapter(request.app.state.redis)
    conv_state_svc = ConversationStateService(
        adapter=adapter,
        ttl_seconds=settings.short_term_memory_ttl_seconds,
        context_size_limit_chars=settings.chat_context_size_limit_chars,
    )
    llm_adapter = getattr(request.app.state, "chat_llm_adapter", None) or FakeLLMAdapter()
    prompt_registry = getattr(request.app.state, "prompt_registry", None)
    if prompt_registry is None:
        prompt_registry = PromptRegistry.from_settings(settings)
    tool_exec_svc = getattr(request.app.state, "chat_tool_execution_service", None)
    if tool_exec_svc is None:
        from app.infra.model_server_tools import FakeModelServerTools
        from app.infra.rag_tool_client import FakeRAGToolClient
        from app.infra.memory_tool_client import FakeMemoryToolClient
        from app.services.chat_rag_snapshot_coordinator import ChatRAGSnapshotCoordinator
        from app.services.tool_execution_service import ToolExecutionService
        class _FakeSnapshotSvc:
            async def store_snapshot(self, **kw):
                from app.domain.rag import SnapshotRecord
                return SnapshotRecord(conversation_id=kw["conversation_id"], message_id=kw["message_id"], trace_id=kw.get("trace_id"), query=kw["query"], chunk_ids=[], scores=[])
        tool_exec_svc = ToolExecutionService(
            model_server_tools=FakeModelServerTools(),
            rag_tool_client=FakeRAGToolClient(),
            memory_tool_client=FakeMemoryToolClient(),
            rag_snapshot_coordinator=ChatRAGSnapshotCoordinator(_FakeSnapshotSvc()),
            per_tool_timeout_seconds=settings.chat_per_tool_timeout_seconds,
        )
    tracing_svc = ChatTracingService(
        getattr(request.app.state, "chat_trace_adapter", None) or FakeTraceAdapter()
    )
    graph_svc = ChatbotGraphService(
        llm_adapter=llm_adapter,
        prompt_registry=prompt_registry,
        tool_execution_service=tool_exec_svc,
        tracing_service=tracing_svc,
    )
    chat_svc = ChatbotService(
        conversation_state_service=conv_state_svc,
        chatbot_graph_service=graph_svc,
        tracing_service=tracing_svc,
        limits=type("ChatLimits", (), {
            "request_size_limit_bytes": settings.chat_request_size_limit_bytes,
            "context_size_limit_chars": settings.chat_context_size_limit_chars,
            "max_tool_calls": settings.chat_max_tool_calls,
            "recursion_limit": settings.chat_recursion_limit,
            "total_timeout_seconds": settings.chat_total_timeout_seconds,
            "per_tool_timeout_seconds": settings.chat_per_tool_timeout_seconds,
        })(),
    )
    return WidgetChatService(chatbot_service=chat_svc)


@router.get("/{widget_id}/config")
async def get_public_widget_config(widget_id: str, request: Request) -> JSONResponse:
    """Return public widget configuration for an approved origin."""
    request_id = getattr(request.state, "request_id", None)
    origin = request.headers.get("origin")
    svc = WidgetEmbedService()
    config_svc = _get_widget_config_service(request)

    try:
        config = await config_svc.get_by_widget_id(widget_id, request_id=request_id)
    except Exception:
        raise WidgetEmbedError(
            "Widget not found",
            details={"widget_id": widget_id},
            trace_id=request_id,
        )

    decision = svc.validate_widget_for_embed(
        is_enabled=config["is_enabled"],
        allowed_origins=config["allowed_origins"],
        requested_origin=origin,
        widget_id=widget_id,
        request_id=request_id,
    )
    if not decision.allowed:
        raise WidgetEmbedError(
            f"Origin not allowed: {decision.reason}",
            details={"widget_id": widget_id, "reason": decision.reason},
            trace_id=request_id,
        )

    public = PublicWidgetConfigRead(
        widget_id=config["widget_id"],
        theme=config.get("theme", "default"),
        greeting=config.get("greeting"),
        position=config.get("position", "bottom-right"),
        enabled_tools=config.get("enabled_tools", []),
    )
    return JSONResponse(
        content=public.model_dump(exclude_none=True),
        headers={
            "Cache-Control": "no-store",
            "X-Request-ID": request_id or "",
        },
    )


@router.post("/{widget_id}/session")
async def issue_widget_session(widget_id: str, request: Request) -> JSONResponse:
    """Issue a widget-scoped anonymous session token."""
    request_id = getattr(request.state, "request_id", None)
    origin = request.headers.get("origin")
    svc = WidgetEmbedService()
    session_svc = WidgetSessionService()
    config_svc = _get_widget_config_service(request)

    try:
        config = await config_svc.get_by_widget_id(widget_id, request_id=request_id)
    except Exception:
        raise WidgetSessionError(
            "Widget not found",
            details={"widget_id": widget_id},
            trace_id=request_id,
        )

    decision = svc.validate_widget_for_embed(
        is_enabled=config["is_enabled"],
        allowed_origins=config["allowed_origins"],
        requested_origin=origin,
        widget_id=widget_id,
        request_id=request_id,
    )
    if not decision.allowed:
        raise WidgetSessionError(
            f"Origin not allowed: {decision.reason}",
            details={"widget_id": widget_id, "reason": decision.reason},
            trace_id=request_id,
        )

    token_data = session_svc.issue_token(
        widget_id=widget_id,
        origin=origin or "",
        request_id=request_id,
    )
    return JSONResponse(
        content=WidgetSessionToken(**token_data).model_dump(exclude_none=True),
        headers={"X-Request-ID": request_id or ""},
    )


@router.post("/{widget_id}/chat/messages")
async def submit_widget_chat_message(widget_id: str, request: Request) -> JSONResponse:
    """Submit a chat message for widget streaming."""
    request_id = getattr(request.state, "request_id", None)
    body = await request.json()
    message = body.get("message", "")
    session_token = body.get("session_token", "")
    conversation_id = body.get("conversation_id")

    if not message:
        return JSONResponse(
            status_code=422,
            content={"error": "message is required"},
            headers={"X-Request-ID": request_id or ""},
        )

    chat_svc = _get_widget_chat_service(request)
    conv_id = await chat_svc.submit_message(
        widget_id=widget_id,
        session_token=session_token,
        message=message,
        conversation_id=conversation_id,
        request_id=request_id,
    )
    return JSONResponse(
        content={"conversation_id": conv_id},
        headers={"X-Request-ID": request_id or ""},
    )


@router.get("/{widget_id}/chat/stream")
async def stream_widget_chat(widget_id: str, request: Request) -> StreamingResponse:
    """Stream widget chat response via SSE."""
    request_id = getattr(request.state, "request_id", None)
    session_token = request.query_params.get("token", "")
    conversation_id = request.query_params.get("conversation_id", "")
    message = request.query_params.get("message", "")

    if not message:
        return StreamingResponse(
            iter(['data: {"event_type":"error","content":"message is required"}\n\n']),
            media_type="text/event-stream",
            headers={"X-Request-ID": request_id or ""},
        )

    chat_svc = _get_widget_chat_service(request)

    async def event_generator():
        async for event in chat_svc.stream_chat(
            widget_id=widget_id,
            session_token=session_token,
            conversation_id=conversation_id,
            message=message,
            request_id=request_id,
        ):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"X-Request-ID": request_id or ""},
    )
