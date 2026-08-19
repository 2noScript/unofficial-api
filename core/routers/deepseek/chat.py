import os
import time
import asyncio
import logging
from typing import AsyncGenerator

from fastapi import Body, Request
from fastapi.responses import JSONResponse, StreamingResponse
from deepseek_api import DeepSeek, DEEPSEEK_MODEL_CONFIG
from core.schemas import ChatCompletionRequest, ChatCompletionResponse
from core.utils import extract_text, make_stream_chunk, make_error_chunk, STREAM_END
from core.session.adapters import get_adapter
from core.session.history import sync_and_get_history, append_assistant_message, format_prompt_with_history
from core.load_balancer import load_balancer, NoActiveProfileError
from core.services.chat_service import chat_service
from core.services.deepseek_strategy import DeepSeekStrategy

from .router import router

logger = logging.getLogger(__name__)
deepseek_strategy = DeepSeekStrategy()





@router.post(
    "/chat/completions",
    summary="Create a chat completion using DeepSeek models",
    response_model=ChatCompletionResponse,
    response_model_exclude_none=True,
)
async def chat_completions(
    request: Request,
    body: ChatCompletionRequest = Body(
        openapi_examples={
            "basic": {
                "summary": "Basic chat",
                "value": {
                    "model": "deepseek-v3",
                    "messages": [{"role": "user", "content": "Hello!"}],
                    "stream": False,
                },
            }
        }
    ),
):
    messages = body.messages
    stream = body.stream
    model = body.model or "deepseek-v3"

    if model.lower() not in DEEPSEEK_MODEL_CONFIG:
        return JSONResponse(
            {"error": {"message": f"Model '{model}' not supported. Supported: {list(DEEPSEEK_MODEL_CONFIG)}", "type": "invalid_request_error", "code": "model_not_found"}},
            status_code=400,
        )

    # Session integration
    adapter = get_adapter("deepseek")

    session_data = getattr(request.state, "session_data", {})

    # Sync local history with incoming messages
    body_messages = [m.model_dump() for m in messages]
    sync_and_get_history(body_messages, session_data)

    if stream:
        return await chat_service.execute_stream(
            strategy=deepseek_strategy,
            request=request,
            messages=body_messages,
            model=model,
            session_data=session_data,
            adapter=adapter,
        )

    return await chat_service.execute_chat(
        strategy=deepseek_strategy,
        request=request,
        messages=body_messages,
        model=model,
        session_data=session_data,
        adapter=adapter,
    )
