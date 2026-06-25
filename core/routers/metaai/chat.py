import os
import sys
import json
import time
import asyncio
from typing import AsyncGenerator

from fastapi import Request, Body
from fastapi.responses import JSONResponse, StreamingResponse
from metaai_api import MetaAI

from .router import router
from .helpers import get_client, _executor
from core.schemas import ChatCompletionRequest, ChatCompletionResponse


@router.post(
    "/chat/completions",
    summary="Create a chat completion using Meta AI (Llama 4)",
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
                    "model": "llama-4",
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
            {"error": "MetaAI client not initialized. Set META_AI_DATR in .env."},
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
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=401)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    content = result.get("message", "") if isinstance(result, dict) else str(result)

    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "llama-4",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": len(content.split()) if content else 0,
            "total_tokens": len(content.split()) if content else 0,
        },
    }


def _run_chat(client: MetaAI, prompt: str) -> dict:
    return client.prompt(message=prompt)


async def _stream_chat(client: MetaAI, prompt: str) -> AsyncGenerator[str, None]:
    try:
        loop = asyncio.get_event_loop()
        gen = await loop.run_in_executor(
            _executor, lambda: client.prompt(message=prompt, stream=True)
        )
        if hasattr(gen, "__iter__"):
            for chunk in gen:
                if isinstance(chunk, dict):
                    text = chunk.get("message", "") or chunk.get("text", "") or ""
                    if text:
                        data = json.dumps({"choices": [{"delta": {"content": text}}]})
                        yield f"data: {data}\n\n"
        else:
            text = gen.get("message", "") if isinstance(gen, dict) else str(gen)
            if text:
                data = json.dumps({"choices": [{"delta": {"content": text}}]})
                yield f"data: {data}\n\n"
    except Exception as e:
        data = json.dumps({"error": str(e)})
        yield f"data: {data}\n\n"
    yield "data: [DONE]\n\n"
