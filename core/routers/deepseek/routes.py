import os
import sys
import json
import time
import asyncio
from typing import AsyncGenerator

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "deepseek-api"))

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse, StreamingResponse
from DeepSeekAPI import DeepSeekChat
from core.schemas import ChatCompletionRequest, ChatCompletionResponse

router = APIRouter(tags=["DeepSeek"])

DEEPSEEK_MODELS = [
    {
        "id": "deepseek-v3",
        "object": "model",
        "created": 1704067200,
        "owned_by": "deepseek",
        "description": "DeepSeek V3 - Fast responses without extended thinking",
    },
    {
        "id": "deepseek-r1",
        "object": "model",
        "created": 1704067200,
        "owned_by": "deepseek",
        "description": "DeepSeek R1 - Reasoning model with extended thinking",
    },
    {
        "id": "deepseek-v4",
        "object": "model",
        "created": 1704067200,
        "owned_by": "deepseek",
        "description": "DeepSeek V4 - Expert model without extended thinking",
    },
    {
        "id": "deepseek-r4",
        "object": "model",
        "created": 1704067200,
        "owned_by": "deepseek",
        "description": "DeepSeek R4 - Expert reasoning model with extended thinking",
    },
    {
        "id": "deepseek-v4-expert",
        "object": "model",
        "created": 1704067200,
        "owned_by": "deepseek",
        "description": "DeepSeek V4 Expert - Expert mode without extended thinking",
    },
    {
        "id": "deepseek-r4-expert",
        "object": "model",
        "created": 1704067200,
        "owned_by": "deepseek",
        "description": "DeepSeek R4 Expert - Expert reasoning model with extended thinking",
    },
]


def _get_auth():
    ds_session_id = os.environ.get("DEEPSEEK_SESSION_ID") or os.environ.get("DS_SESSION_ID")
    auth_token = os.environ.get("DEEPSEEK_AUTH_TOKEN") or os.environ.get("AUTHORIZATION_TOKEN")
    if not ds_session_id or not auth_token:
        raise ValueError(
            "DeepSeek credentials not found. Set DEEPSEEK_SESSION_ID and DEEPSEEK_AUTH_TOKEN"
        )
    if not auth_token.startswith("Bearer "):
        auth_token = f"Bearer {auth_token}"
    return ds_session_id, auth_token


def _get_model_config(model: str):
    model_lower = model.lower()
    is_expert = "expert" in model_lower
    model_type = "expert" if is_expert else "default"
    thinking_enabled = "r1" in model_lower or "r4" in model_lower or "reasoning" in model_lower or "reasoner" in model_lower
    # Normalize base model name for display
    if is_expert:
        base = model_lower.replace("-expert", "")
    else:
        base = model_lower
    return model_type, thinking_enabled, base


def _run_chat(messages: list, model_type: str, thinking_enabled: bool, search_enabled: bool) -> dict:
    ds_session_id, auth_token = _get_auth()
    user_message = messages[-1].content if messages else ""

    last_error: str = "Unknown error"

    for attempt in range(2):  # retry once for WASM warm-up on first call
        chat = DeepSeekChat(ds_session_id, auth_token)
        result = chat.send_message(
            user_message,
            thinking_enabled=thinking_enabled,
            search_enabled=search_enabled,
            model_type=model_type,
        )

        if result is None:
            last_error = "DeepSeek returned no response. Check credentials or session."
            continue

        if not isinstance(result, dict):
            last_error = f"Unexpected response type from DeepSeek: {result}"
            continue

        if not result.get("ok"):
            err = result.get("content", "Unknown error")
            if isinstance(err, (bytes, bytearray)):
                err = err.decode("utf-8", errors="replace")
            last_error = f"DeepSeek error: {err}"
            continue

        # success
        content = result.get("content", {})
        if isinstance(content, dict):
            return content
        return {"response": str(content)}

    raise RuntimeError(last_error)


async def _stream_chat(messages: list, model_type: str, thinking_enabled: bool, search_enabled: bool) -> AsyncGenerator[str, None]:
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, _run_chat, messages, model_type, thinking_enabled, search_enabled
        )
        text = result.get("response", "")
        for line in text.split("\n"):
            if line.strip():
                chunk = json.dumps({"choices": [{"delta": {"content": line + "\n"}}]})
                yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
    except ValueError as e:
        data = json.dumps({"error": str(e)})
        yield f"data: {data}\n\n"
    except Exception as e:
        data = json.dumps({"error": str(e)})
        yield f"data: {data}\n\n"


@router.get("/models", summary="List available DeepSeek models")
async def list_models():
    return {"object": "list", "data": DEEPSEEK_MODELS}


@router.post(
    "/chat/completions",
    summary="Create a chat completion using DeepSeek models",
    response_model=ChatCompletionResponse,
    response_model_exclude_none=True,
)
async def chat_completions(
    body: ChatCompletionRequest = Body(
        openapi_examples={
            "basic": {
                "summary": "Basic chat",
                "value": {
                    "model": "deepseek-v3",
                    "messages": [{"role": "user", "content": "Hello!"}],
                },
            }
        }
    )
):
    messages = body.messages
    stream = body.stream
    model = body.model or "deepseek-v3"

    model_type, thinking_enabled, _ = _get_model_config(model)

    try:
        if stream:
            return StreamingResponse(
                _stream_chat(messages, model_type, thinking_enabled, False),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
            )

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, _run_chat, messages, model_type, thinking_enabled, False
        )
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=401)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    response_text = result.get("response", "")
    thought = result.get("thought")

    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text,
                    "reasoning_content": thought,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": len(response_text.split()) if response_text else 0,
            "total_tokens": len(response_text.split()) if response_text else 0,
        },
        "citation": result.get("citation"),
        "title": result.get("title"),
    }
