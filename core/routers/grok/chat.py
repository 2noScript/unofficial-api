import json
import time
from typing import AsyncGenerator

from fastapi import Request, Body
from fastapi.responses import JSONResponse, StreamingResponse

from app.control.model.enums import ModeId
from app.control.model.registry import get as get_model_spec

from .router import router
from .helpers import get_client
from core.schemas import ChatCompletionRequest, ChatCompletionResponse


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
    prompt = messages[-1].content if messages else ""

    if not prompt:
        return JSONResponse({"error": "No prompt provided"}, status_code=400)

    if stream:
        return StreamingResponse(
            _stream_chat(client, prompt, mode_id),
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


async def _stream_chat(client, prompt: str, mode_id: ModeId) -> AsyncGenerator[str, None]:
    try:
        result = await client.send_message(prompt, mode_id=mode_id)
        for token in result.split():
            chunk = json.dumps({"choices": [{"delta": {"content": token + " "}}]})
            yield f"data: {chunk}\n\n"
    except Exception as e:
        data = json.dumps({"error": str(e)})
        yield f"data: {data}\n\n"
    yield "data: [DONE]\n\n"
