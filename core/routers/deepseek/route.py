import os
import sys
import json
import time
import asyncio
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "deepseek-api"))

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse, StreamingResponse
from DeepSeekAPI import DeepSeekChat
from core.schemas import ChatCompletionRequest, ChatCompletionResponse
from core.stream import make_stream_chunk, make_error_chunk, STREAM_END
from core.utils import extract_text
from core.session.adapters import get_adapter

router = APIRouter(tags=["DeepSeek"])

DEEPSEEK_MODEL_CONFIG = {
    "deepseek-v3": {"model_type": "default", "thinking": False},
    "deepseek-r1": {"model_type": "default", "thinking": False},
    "deepseek-v4": {"model_type": "default", "thinking": False},
    "deepseek-r4": {"model_type": "default", "thinking": False},
}

DEEPSEEK_MODELS = [
    {
        "id": "deepseek-v3",
        "object": "model",
        "created": 1704067200,
        "owned_by": "deepseek",
        "description": "Default model without extended thinking",
    },
    {
        "id": "deepseek-r1",
        "object": "model",
        "created": 1704067200,
        "owned_by": "deepseek",
        "description": "Default model with extended thinking",
    },
    {
        "id": "deepseek-v4",
        "object": "model",
        "created": 1704067200,
        "owned_by": "deepseek",
        "description": "Default model without extended thinking",
    },
    {
        "id": "deepseek-r4",
        "object": "model",
        "created": 1704067200,
        "owned_by": "deepseek",
        "description": "Default model with extended thinking",
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
    key = model.lower()
    config = DEEPSEEK_MODEL_CONFIG.get(key, DEEPSEEK_MODEL_CONFIG["deepseek-v3"])
    return config["model_type"], config["thinking"], key


def _parse_deepseek_error(err: str) -> tuple[int, str]:
    import re
    m = re.match(r"HTTP (\d+): (.+)", err)
    if m:
        return int(m.group(1)), m.group(2).strip()
    return 500, err


def _run_chat(messages: list, model_type: str, thinking_enabled: bool, search_enabled: bool, session_data: dict, adapter) -> dict:
    ds_session_id, auth_token = _get_auth()
    user_message = extract_text(messages[-1].content) if messages else ""

    last_error: str = "Unknown error"
    last_status: int = 500

    for attempt in range(2):  # retry once for WASM warm-up on first call
        chat = DeepSeekChat(ds_session_id, auth_token)
        adapter.inject(session_data, {'chat': chat})
        
        result = chat.send_message(
            user_message,
            thinking_enabled=thinking_enabled,
            search_enabled=search_enabled,
            model_type=model_type,
        )

        if not isinstance(result, dict):
            last_error = f"Unexpected response type from DeepSeek: {result}"
            continue

        if not result.get("ok"):
            err = result.get("content", "Unknown error")
            if isinstance(err, (bytes, bytearray)):
                err = err.decode("utf-8", errors="replace")
            last_status, last_error = _parse_deepseek_error(err)
            continue

        # success
        session_data.update(adapter.extract({'_chat_instance': chat}, session_data))
        
        content = result.get("content", {})
        if isinstance(content, dict):
            return content
        return {"response": str(content)}

    if last_status in (401, 403):
        raise ValueError(last_error)
    raise RuntimeError(last_error)


async def _stream_chat_fake(messages: list, model: str, model_type: str, thinking_enabled: bool, search_enabled: bool, session_data: dict, adapter) -> AsyncGenerator[str, None]:
    response_id = f"chatcmpl-{int(time.time())}"
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, _run_chat, messages, model_type, thinking_enabled, search_enabled, session_data, adapter
        )
        text = result.get("response", "")
        first = True
        for line in text.split("\n"):
            if line.strip():
                yield make_stream_chunk(model, line + "\n", response_id, is_first=first)
                first = False
        if not first:
            yield make_stream_chunk(model, "", response_id, is_final=True)
        yield STREAM_END
    except ValueError as e:
        yield make_error_chunk(str(e), "authentication_error", "invalid_credentials")
        yield STREAM_END
    except Exception as e:
        yield make_error_chunk(str(e), "server_error", "upstream_error")
        yield STREAM_END


async def _stream_chat_real(messages: list, model: str, model_type: str, thinking_enabled: bool, search_enabled: bool, session_data: dict, adapter) -> AsyncGenerator[str, None]:
    try:
        ds_session_id, auth_token = _get_auth()
        user_message = extract_text(messages[-1].content) if messages else ""
        response_id = f"chatcmpl-{int(time.time())}"

        queue = asyncio.Queue()
        loop = asyncio.get_event_loop()
        sentinel = object()

        def on_text(chunk: str):
            loop.call_soon_threadsafe(queue.put_nowait, chunk)

        def _send() -> dict:
            """Call send_message with retry, without sentinel."""
            for attempt in range(2):
                try:
                    chat = DeepSeekChat(ds_session_id, auth_token)
                    adapter.inject(session_data, {'chat': chat})
                    
                    result = chat.send_message(
                        user_message,
                        thinking_enabled=thinking_enabled,
                        search_enabled=search_enabled,
                        model_type=model_type,
                        text_callback=on_text,
                    )
                    if result.get("ok"):
                        session_data.update(adapter.extract({'_chat_instance': chat}, session_data))
                        return result
                    logger.warning("DeepSeek send attempt %d failed", attempt + 1)
                except Exception as e:
                    if attempt == 0:
                        logger.warning("DeepSeek send attempt %d threw: %s", attempt + 1, e)
                        continue
                    raise
            return {"ok": False, "content": "DeepSeek failed after retry"}

        def run() -> dict:
            try:
                return _send()
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, sentinel)

        task = loop.run_in_executor(None, run)

        first = True
        while True:
            chunk = await queue.get()
            if chunk is sentinel:
                break
            yield make_stream_chunk(model, chunk, response_id, is_first=first)
            first = False

        result = await task

        if not result.get("ok"):
            err = result.get("content", "Unknown error")
            if isinstance(err, (bytes, bytearray)):
                err = err.decode("utf-8", errors="replace")
            yield make_error_chunk(str(err))
            yield STREAM_END
            return

        if not first:
            yield make_stream_chunk(model, "", response_id, is_final=True)
        yield STREAM_END

    except ValueError as e:
        yield make_error_chunk(str(e), "authentication_error", "invalid_credentials")
        yield STREAM_END
    except Exception as e:
        yield make_error_chunk(str(e), "server_error", "upstream_error")
        yield STREAM_END


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
    )
):
    messages = body.messages
    stream = body.stream
    model = body.model or "deepseek-v3"

    model_type, thinking_enabled, _ = _get_model_config(model)
    logger.info("Request /v1/deepseek/chat/completions: %s", body.model_dump_json())

    # Session integration
    adapter = get_adapter("deepseek")
    session_data = getattr(request.state, "session_data", {})

    try:
        if stream:
            return StreamingResponse(
                _stream_chat_real(messages, model, model_type, thinking_enabled, False, session_data, adapter),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
            )

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, _run_chat, messages, model_type, thinking_enabled, False, session_data, adapter
        )
    except ValueError as e:
        return JSONResponse(
            {"error": {"message": str(e), "type": "authentication_error", "code": "invalid_credentials"}},
            status_code=401,
        )
    except Exception as e:
        return JSONResponse(
            {"error": {"message": str(e), "type": "server_error", "code": "upstream_error"}},
            status_code=500,
        )

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
    }
