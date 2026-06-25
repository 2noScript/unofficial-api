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
    messages = body.messages
    stream = body.stream
    prompt = extract_text(messages[-1].content) if messages else ""

    if not prompt:
        return JSONResponse({"error": "No prompt provided"}, status_code=400)
    logger.info("Request /v1/grok/chat/completions: %s", body.model_dump_json())

    if stream:
        return StreamingResponse(
            _stream_chat(client, model, prompt, mode_id),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    try:
        result = await client.send_message(prompt, mode_id=mode_id)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

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


async def _stream_chat(client, model: str, prompt: str, mode_id: ModeId) -> AsyncGenerator[str, None]:
    response_id = f"chatcmpl-{int(time.time())}"
    try:
        result = await client.send_message(prompt, mode_id=mode_id)
        first = True
        for token in result.split():
            yield make_stream_chunk(model, token + " ", response_id, is_first=first)
            first = False
        if not first:
            yield make_stream_chunk(model, "", response_id, is_final=True)
        yield STREAM_END
    except Exception as e:
        yield make_error_chunk(str(e))
        yield STREAM_END
