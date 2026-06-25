import json
import time
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

from fastapi import Request, Body
from fastapi.responses import JSONResponse, StreamingResponse

from app.control.model.enums import ModeId
from app.control.model.registry import get as get_model_spec

from .router import router
from .helpers import get_client
from core.schemas import ChatCompletionRequest, ChatCompletionResponse
from core.stream import make_stream_chunk, make_error_chunk, STREAM_END
from core.utils import extract_text
from core.session.adapters import get_adapter
from core.session.history import sync_and_get_history, append_assistant_message, format_prompt_with_history


def _resolve_mode_id(model_name: str) -> ModeId:
    spec = get_model_spec(model_name)
    return spec.mode_id if spec else ModeId.AUTO


@router.post(
    "/chat/completions",
    summary="Create a chat completion using Grok",
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
                    "model": "grok-4.20-auto",
                    "messages": [{"role": "user", "content": "Hello!"}],
                    "stream": False,
                },
            }
        }
    )
):
    client = get_client(request)
    if not client:
        return JSONResponse(
            {"error": "Grok client not initialized. Set GROK_PROXY_CF_COOKIES in .env."},
            status_code=503,
        )

    model = body.model or "grok-4.20-auto"
    mode_id = _resolve_mode_id(model)
    messages = [m.model_dump() for m in body.messages]
    stream = body.stream
    raw_prompt = extract_text(messages[-1].get("content")) if messages else ""

    if not raw_prompt:
        return JSONResponse({"error": "No prompt provided"}, status_code=400)
    logger.info("Request /v1/grok/chat/completions: %s", body.model_dump_json())

    # Session integration
    adapter = get_adapter("grok")
    session_data = getattr(request.state, "session_data", {})

    # Sync local history with incoming messages
    sync_and_get_history(messages, session_data)
    history = session_data.get("history", [])

    prompt = format_prompt_with_history(history, raw_prompt)

    if stream:
        return StreamingResponse(
            _stream_chat(client, model, prompt, mode_id, session_data),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    try:
        result = await client.send_message(prompt, mode_id=mode_id)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    append_assistant_message(session_data, result)

    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": result},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": len(result.split()) if result else 0,
            "total_tokens": len(result.split()) if result else 0,
        },
    }


async def _stream_chat(
    client, model: str, prompt: str, mode_id: ModeId, session_data: dict
) -> AsyncGenerator[str, None]:
    response_id = f"chatcmpl-{int(time.time())}"
    try:
        result = await client.send_message(prompt, mode_id=mode_id)
        first = True
        for token in result.split():
            yield make_stream_chunk(model, token + " ", response_id, is_first=first)
            first = False
        if not first:
            yield make_stream_chunk(model, "", response_id, is_final=True)
        append_assistant_message(session_data, result)
        yield STREAM_END
    except Exception as e:
        yield make_error_chunk(str(e))
        yield STREAM_END

