import os
import sys
import json
import time
import asyncio
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

from fastapi import Request, Body
from fastapi.responses import JSONResponse, StreamingResponse
from metaai_api import MetaAI

from .router import router
from .helpers import get_client, _executor
from core.schemas import ChatCompletionRequest, ChatCompletionResponse
from core.stream import make_stream_chunk, make_error_chunk, STREAM_END
from core.utils import extract_text
from core.session.adapters import get_adapter
from core.session.history import sync_and_get_history, append_assistant_message, format_prompt_with_history


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

    messages = [m.model_dump() for m in body.messages]
    stream = body.stream
    raw_prompt = extract_text(messages[-1].get("content")) if messages else ""

    if not raw_prompt:
        return JSONResponse({"error": "No prompt provided"}, status_code=400)
    logger.info("Request /v1/metaai/chat/completions: %s", body.model_dump_json())

    # Session integration
    adapter = get_adapter("metaai")
    session_data = getattr(request.state, "session_data", {})

    # Sync local history with incoming messages
    sync_and_get_history(messages, session_data)
    history = session_data.get("history", [])

    prompt = format_prompt_with_history(history, raw_prompt)

    if stream:
        return StreamingResponse(
            _stream_chat(client, "llama-4", prompt, session_data),
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
    append_assistant_message(session_data, content)

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


async def _stream_chat(
    client: MetaAI, model: str, prompt: str, session_data: dict
) -> AsyncGenerator[str, None]:
    response_id = f"chatcmpl-{int(time.time())}"
    try:
        loop = asyncio.get_event_loop()
        gen = await loop.run_in_executor(
            _executor, lambda: client.prompt(message=prompt, stream=True)
        )
        first = True
        collected = []
        if hasattr(gen, "__iter__"):
            for chunk in gen:
                if isinstance(chunk, dict):
                    text = chunk.get("message", "") or chunk.get("text", "") or ""
                    if text:
                        collected.append(text)
                        yield make_stream_chunk(model, text, response_id, is_first=first)
                        first = False
        else:
            text = gen.get("message", "") if isinstance(gen, dict) else str(gen)
            if text:
                collected.append(text)
                yield make_stream_chunk(model, text, response_id, is_first=first)
                first = False
        if not first:
            yield make_stream_chunk(model, "", response_id, is_final=True)
        
        full_text = "".join(collected)
        append_assistant_message(session_data, full_text)
        yield STREAM_END
    except Exception as e:
        yield make_error_chunk(str(e))
        yield STREAM_END

