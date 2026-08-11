import os
import json
import time
import asyncio
import logging
import functools
from typing import AsyncGenerator


from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse, StreamingResponse
from deepseek_api import DeepSeek, DEEPSEEK_MODELS, DEEPSEEK_MODEL_CONFIG
from core.schemas import ChatCompletionRequest, ChatCompletionResponse
from core.utils import extract_text, make_stream_chunk, make_error_chunk, STREAM_END
from core.session.adapters import get_adapter
from core.session.history import sync_and_get_history, append_assistant_message, format_prompt_with_history


from core.load_balancer import load_balancer, NoActiveProfileError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["DeepSeek"])


def _get_auth(session_data: dict | None = None) -> str:
    try:
        profile, _ = load_balancer.select_profile("deepseek", session_data=session_data)
        auth_token = profile.get("token", "")
    except NoActiveProfileError:
        auth_token = os.environ.get("DEEPSEEK_AUTH_TOKEN")
        if not auth_token:
            raise ValueError(
                "DeepSeek credentials not found. Create a DeepSeek profile or set DEEPSEEK_AUTH_TOKEN."
            )
    if not auth_token.startswith("Bearer "):
        auth_token = f"Bearer {auth_token}"
    return auth_token


def _parse_deepseek_error(err: str) -> tuple[int, str]:
    import re
    m = re.match(r"HTTP (\d+): (.+)", err)
    if m:
        return int(m.group(1)), m.group(2).strip()
    return 500, err


def _is_session_error(err: str) -> bool:
    session_keywords = (
        "session", "401", "403", "unauthorized", "login",
        "token", "expired", "invalid", "auth", "40300"
    )
    lower = err.lower()
    return any(kw in lower for kw in session_keywords)


def _build_prompt(history: list[dict], user_message: str, has_provider_session: bool) -> str:
    """If provider session exists, only send user message. Otherwise format full transcript."""
    if has_provider_session:
        return user_message
    return format_prompt_with_history(history, user_message)


def _run_chat(
    messages: list,
    model: str,
    session_data: dict,
    adapter,
) -> dict:
    active_profiles = load_balancer.get_active_profiles("deepseek")
    max_attempts = max(1, len(active_profiles))

    for attempt in range(max_attempts):
        profile_id = None
        try:
            profile, _ = load_balancer.select_profile("deepseek", session_data=session_data)
            profile_id = profile.get("id")
            auth_token = profile.get("token", "")
        except NoActiveProfileError:
            auth_token = os.environ.get("DEEPSEEK_AUTH_TOKEN")
            if not auth_token:
                raise ValueError(
                    "DeepSeek credentials not found. Create a DeepSeek profile or set DEEPSEEK_AUTH_TOKEN."
                )

        if not auth_token.startswith("Bearer "):
            auth_token = f"Bearer {auth_token}"

        user_message = extract_text(messages[-1].content) if messages else ""
        history = session_data.get("history", [])

        has_provider_session = bool(session_data.get("deepseek_chat_session_id")) and not session_data.get("deepseek_force_virtual")
        prompt = _build_prompt(history, user_message, has_provider_session)
        session_kwargs = adapter.inject(session_data, {})

        client = DeepSeek(auth_token)
        chat = client.new_session(**session_kwargs)

        result = chat.send_message(prompt, model=model)

        if not result.get("ok"):
            err_msg = result.get("content", "Unknown error")
            if isinstance(err_msg, (bytes, bytearray)):
                err_msg = err_msg.decode("utf-8", errors="replace")
            last_status, last_error = _parse_deepseek_error(err_msg)

            if load_balancer.is_retryable_error(last_error) or last_status in (401, 403, 429):
                logger.warning("DeepSeek profile '%s' failed with auth/rate-limit error (%s). Failing over...", profile_id, last_error)
                if profile_id:
                    load_balancer.handle_profile_failure(profile_id, session_data)
                session_data["deepseek_force_virtual"] = True
                if attempt < max_attempts - 1 and load_balancer.get_active_profiles("deepseek"):
                    continue
                raise ValueError(last_error)
            raise RuntimeError(last_error)

        if not session_data.get("deepseek_force_virtual"):
            session_data.update(adapter.extract({"_chat_instance": chat}, session_data))

        content = result.get("content", {})
        if isinstance(content, dict):
            response_text = content.get("response", "")
            append_assistant_message(session_data, response_text)
            return content
        text = str(content)
        append_assistant_message(session_data, text)
        return {"response": text}

    raise RuntimeError("All DeepSeek profile attempts failed.")


async def _stream_chat_real(
    messages: list,
    model: str,
    session_data: dict,
    adapter,
) -> AsyncGenerator[str, None]:
    try:
        auth_token = _get_auth(session_data)
        user_message = extract_text(messages[-1].content) if messages else ""
        history = session_data.get("history", [])
        response_id = f"chatcmpl-{int(time.time())}"

        has_provider_session = bool(session_data.get("deepseek_chat_session_id")) and not session_data.get("deepseek_force_virtual")
        prompt = _build_prompt(history, user_message, has_provider_session)

        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def run() -> dict:
            try:
                session_kwargs = adapter.inject(session_data, {})
                client = DeepSeek(auth_token)
                chat = client.new_session(**session_kwargs)

                for event_type, content in chat.send_message_stream(
                    prompt,
                    model=model,
                ):
                    if event_type == "error":
                        return {"ok": False, "content": content}
                    elif event_type in ("content", "thought"):
                        loop.call_soon_threadsafe(queue.put_nowait, content)

                session_data.update(adapter.extract({"_chat_instance": chat}, session_data))
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "content": str(e)}

        t = loop.run_in_executor(None, run)

        collected_text = []
        first = True
        while True:
            get_task = asyncio.create_task(queue.get())
            done, _ = await asyncio.wait([get_task, t], return_when=asyncio.FIRST_COMPLETED)

            if get_task in done:
                chunk_text = get_task.result()
                collected_text.append(chunk_text)
                chunk_str = make_stream_chunk(model, chunk_text, response_id, is_first=first)
                yield chunk_str
                first = False
            else:
                get_task.cancel()
                res = t.result()
                if not res.get("ok"):
                    err_msg = res.get("content", "Stream error")
                    yield make_error_chunk(err_msg)
                    yield STREAM_END
                    return
                else:
                    full_response = "".join(collected_text)
                    append_assistant_message(session_data, full_response)
                    yield make_stream_chunk(model, "", response_id, is_final=True)
                    yield STREAM_END
                    return

    except Exception as e:
        logger.error("DeepSeek streaming failed: %s", e)
        yield make_error_chunk(str(e))
        yield STREAM_END


@router.get(
    "/models",
    summary="List available DeepSeek models",
)
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

    if model.lower() not in DEEPSEEK_MODEL_CONFIG:
        return JSONResponse(
            {"error": {"message": f"Model '{model}' not supported. Supported: {list(DEEPSEEK_MODEL_CONFIG)}", "type": "invalid_request_error", "code": "model_not_found"}},
            status_code=400,
        )

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
                _stream_chat_real(messages, model, session_data, adapter),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
            )

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, functools.partial(_run_chat, messages, model, session_data, adapter)
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
