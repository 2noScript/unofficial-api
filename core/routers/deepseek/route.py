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
from core.session.history import sync_and_get_history, append_assistant_message, format_prompt_with_history

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


def _is_session_error(err: str) -> bool:
    """Detect provider-side chat session errors that require a new session."""
    if not err:
        return False
    low = err.lower()
    return any(k in low for k in [
        "chat session not found",
        "session_not_found",
        "missing_header",
        "invalid session",
        "chat not found",
    ])


def _build_prompt(history: list[dict], user_message: str, has_provider_session: bool) -> str:
    """Return the prompt to send to DeepSeek.

    If we have an active provider session, send only the current user message.
    Otherwise, embed the full history as a transcript in the prompt.
    """
    if has_provider_session:
        return user_message
    return format_prompt_with_history(history, user_message)


def _run_chat(
    messages: list,
    model_type: str,
    thinking_enabled: bool,
    search_enabled: bool,
    session_data: dict,
    adapter,
) -> dict:
    ds_session_id, auth_token = _get_auth()
    user_message = extract_text(messages[-1].content) if messages else ""
    history = session_data.get("history", [])
    has_provider_session = bool(session_data.get("deepseek_chat_session_id"))

    last_error: str = "Unknown error"
    last_status: int = 500

    for attempt in range(3):  # up to 3 attempts: normal → session-reset → final
        prompt = _build_prompt(history, user_message, has_provider_session and attempt == 0)
        chat = DeepSeekChat(ds_session_id, auth_token)
        adapter.inject(session_data, {"chat": chat})

        result = chat.send_message(
            prompt,
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

            # If provider session is broken, reset and retry with history transcript
            if _is_session_error(err) and has_provider_session:
                logger.warning("DeepSeek session error, resetting provider session: %s", err)
                adapter.clear_provider_session(session_data)
                has_provider_session = False
                continue

            continue

        # Success — persist session state
        session_data.update(adapter.extract({"_chat_instance": chat}, session_data))

        content = result.get("content", {})
        if isinstance(content, dict):
            response_text = content.get("response", "")
            append_assistant_message(session_data, response_text)
            return content
        text = str(content)
        append_assistant_message(session_data, text)
        return {"response": text}

    if last_status in (401, 403):
        raise ValueError(last_error)
    raise RuntimeError(last_error)


async def _stream_chat_fake(
    messages: list,
    model: str,
    model_type: str,
    thinking_enabled: bool,
    search_enabled: bool,
    session_data: dict,
    adapter,
) -> AsyncGenerator[str, None]:
    response_id = f"chatcmpl-{int(time.time())}"
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, _run_chat, messages, model_type, thinking_enabled, search_enabled, session_data, adapter
        )
        text = result.get("response", "")
        first = True
        for line in text.split("\n"):
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


async def _stream_chat_real(
    messages: list,
    model: str,
    model_type: str,
    thinking_enabled: bool,
    search_enabled: bool,
    session_data: dict,
    adapter,
) -> AsyncGenerator[str, None]:
    try:
        ds_session_id, auth_token = _get_auth()
        user_message = extract_text(messages[-1].content) if messages else ""
        history = session_data.get("history", [])
        response_id = f"chatcmpl-{int(time.time())}"

        # We may retry once after a provider session reset
        for attempt in range(2):
            has_provider_session = bool(session_data.get("deepseek_chat_session_id")) and attempt == 0
            prompt = _build_prompt(history, user_message, has_provider_session)

            queue: asyncio.Queue = asyncio.Queue()
            loop = asyncio.get_event_loop()
            sentinel = object()

            def on_text(chunk: str):
                loop.call_soon_threadsafe(queue.put_nowait, chunk)

            def _send() -> dict:
                last_err = "Unknown error"
                for inner_attempt in range(2):
                    try:
                        chat = DeepSeekChat(ds_session_id, auth_token)
                        adapter.inject(session_data, {"chat": chat})

                        result = chat.send_message(
                            prompt,
                            thinking_enabled=thinking_enabled,
                            search_enabled=search_enabled,
                            model_type=model_type,
                            text_callback=on_text,
                        )
                        if result.get("ok"):
                            session_data.update(adapter.extract({"_chat_instance": chat}, session_data))
                            return result
                        last_err = result.get("content", "Unknown error")
                        if isinstance(last_err, (bytes, bytearray)):
                            last_err = last_err.decode("utf-8", errors="replace")
                        logger.warning("DeepSeek send attempt %d.%d failed: %s", attempt + 1, inner_attempt + 1, last_err)
                    except Exception as e:
                        last_err = str(e)
                        logger.warning("DeepSeek send attempt %d.%d threw: %s", attempt + 1, inner_attempt + 1, e)
                        if inner_attempt == 0:
                            continue
                        raise
                logger.error("DeepSeek failed after inner retries: %s", last_err)
                return {"ok": False, "content": last_err}

            def run() -> dict:
                try:
                    return _send()
                finally:
                    loop.call_soon_threadsafe(queue.put_nowait, sentinel)

            task = loop.run_in_executor(None, run)

            # Collect streamed text while the thread is running
            collected_text = []
            first = True
            while True:
                chunk = await queue.get()
                if chunk is sentinel:
                    break
                collected_text.append(chunk)
                yield make_stream_chunk(model, chunk, response_id, is_first=first)
                first = False

            result = await task

            if not result.get("ok"):
                err = result.get("content", "Unknown error")
                if isinstance(err, (bytes, bytearray)):
                    err = err.decode("utf-8", errors="replace")

                # If provider session error and first attempt, reset and retry
                if _is_session_error(err) and attempt == 0 and bool(session_data.get("deepseek_chat_session_id")):
                    logger.warning("DeepSeek stream session error, resetting provider session: %s", err)
                    adapter.clear_provider_session(session_data)
                    continue

                yield make_error_chunk(str(err))
                yield STREAM_END
                return

            # Append assistant text to history on success
            full_response = "".join(collected_text)
            append_assistant_message(session_data, full_response)

            if not first:
                yield make_stream_chunk(model, "", response_id, is_final=True)
            yield STREAM_END
            return  # success — exit the retry loop

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
    ),
):
    messages = body.messages
    stream = body.stream
    model = body.model or "deepseek-v3"

    model_type, thinking_enabled, _ = _get_model_config(model)
    logger.info("Request /v1/deepseek/chat/completions: %s", body.model_dump_json())

    # Session integration
    adapter = get_adapter("deepseek")
    session_data = getattr(request.state, "session_data", {})

    # Sync local history with incoming messages
    body_messages = [m.model_dump() for m in messages]
    sync_and_get_history(body_messages, session_data)

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
