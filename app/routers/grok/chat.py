import json
import time
import asyncio
from typing import AsyncGenerator

from fastapi import Request, Body
from fastapi.responses import JSONResponse, StreamingResponse

from .router import router
from .helpers import get_client, _executor
from app.schemas import ChatCompletionRequest, ChatCompletionResponse


@router.post(
    "/chat/completions",
    summary="Create a chat completion using Grok 3",
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
                    "model": "grok-3",
                    "messages": [{"role": "user", "content": "Hello!"}],
                },
            }
        }
    )
):
    client = get_client(request)
    if not client:
        return JSONResponse(
            {"error": "Grok client not initialized. Set GROK_SSO and GROK_SSO_RW in .env."},
            status_code=503,
        )

    messages = body.messages
    stream = body.stream
    prompt = messages[-1].content if messages else ""

    if not prompt:
        return JSONResponse({"error": "No prompt provided"}, status_code=400)

    if stream:
        return StreamingResponse(
            _stream_chat(client, prompt),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(_executor, _run_chat, client, prompt)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "grok-3",
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


def _run_chat(client, prompt: str) -> str:
    return client.send_message(message=prompt)


async def _stream_chat(client, prompt: str) -> AsyncGenerator[str, None]:
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(_executor, _run_chat, client, prompt)
        for token in result.split():
            chunk = json.dumps({"choices": [{"delta": {"content": token + " "}}]})
            yield f"data: {chunk}\n\n"
    except Exception as e:
        data = json.dumps({"error": str(e)})
        yield f"data: {data}\n\n"
    yield "data: [DONE]\n\n"
