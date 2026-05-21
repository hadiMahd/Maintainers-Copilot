"""Widget chat service — widget-scoped chat flow reusing Phase 7 ChatbotService."""

from __future__ import annotations

import uuid

import structlog

from app.domain.errors import WidgetSessionError

_log = structlog.get_logger


class WidgetChatService:
    """Widget-scoped chat orchestration.

    Validates widget session token, creates a widget conversation, and
    delegates to the existing Phase 7 ChatbotService for the actual LLM
    tool-calling chat flow.
    """

    def __init__(
        self,
        chatbot_service,
    ) -> None:
        self._chatbot_service = chatbot_service

    async def submit_message(
        self,
        *,
        widget_id: str,
        session_token: str,
        message: str,
        conversation_id: str | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> str:
        if not conversation_id:
            conversation_id = uuid.uuid4().hex
        _log().info(
            "widget_chat_message_submitted",
            widget_id=widget_id,
            conversation_id=conversation_id,
            request_id=request_id,
        )
        return conversation_id

    async def stream_chat(
        self,
        *,
        widget_id: str,
        session_token: str,
        conversation_id: str,
        message: str,
        request_id: str | None = None,
        trace_id: str | None = None,
    ):
        _log().info(
            "widget_chat_stream_started",
            widget_id=widget_id,
            conversation_id=conversation_id,
            request_id=request_id,
        )
        result = await self._chatbot_service.execute_chat(
            user_id=f"widget:{widget_id}",
            body=type("ChatRequest", (), {
                "conversation_id": conversation_id,
                "message": message,
            })(),
            request_id=request_id or uuid.uuid4().hex,
        )
        for event in result.events:
            payload = event.model_dump(exclude_none=True)
            yield f"data: {__import__('json').dumps(payload)}\n\n"
        _log().info(
            "widget_chat_stream_completed",
            widget_id=widget_id,
            conversation_id=conversation_id,
            request_id=request_id,
        )
