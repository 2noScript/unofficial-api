import json
import time
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

from fastapi import Request, Body
from fastapi.responses import JSONResponse, StreamingResponse
from gemini_webapi import GeminiClient, ChatSession

from .router import router
from .helpers import _require_client, _resolve_model_name
from core.schemas import ChatCompletionRequest, ChatCompletionResponse
from core.stream import make_stream_chunk, make_error_chunk, STREAM_END
from core.utils import extract_text
from core.session.adapters import get_adapter
from core.session.history import sync_and_get_history, append_assistant_message, format_prompt_with_history


def _build_chat_session(client: GeminiClient, session_data: dict) -> ChatSession:
    """Create a ChatSession from stored session state, if any."""
    metadata = session_data.get("gemini_metadata")
    if metadata:
        return ChatSession(geminiclient=client, metadata=metadata)
    cid = session_data.get("gemini_cid", "")
    return ChatSession(geminiclient=client, cid=cid)


def _has_provider_session(session_data: dict) -> bool:
    return bool(session_data.get("gemini_cid") or session_data.get("gemini_metadata"))


@router.post(
    "/chat/completions",
    summary="Create a chat completion using Gemini models",
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
                    "model": "gemini-3-flash",
                    "messages": [{"role": "user", "content": "Hello!"}],
                    "stream": False,
                },
            }
        }
    ),
):
    client = _require_client(request)
    if isinstance(client, JSONResponse):
        return client

    messages = [m.model_dump() for m in body.messages]
    stream = body.stream
    model = body.model or "gemini-3-flash"

    resolved_model = _resolve_model_name(model)
    raw_prompt = extract_text(messages[-1].get("content")) if messages else ""
    logger.info("Request /v1/gemini/chat/completions: %s", body.model_dump_json())

    # Session integration
    adapter = get_adapter("gemini")
    session_data = getattr(request.state, "session_data", {})

    # Sync local history with incoming messages
    sync_and_get_history(messages, session_data)
    history = session_data.get("history", [])

    if stream:
        return StreamingResponse(
            _stream_gemini(client, raw_prompt, resolved_model, session_data, adapter, history),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    # Non-streaming with retry-on-session-error
    for attempt in range(2):
        has_session = _has_provider_session(session_data) and attempt == 0
        prompt = raw_prompt if has_session else format_prompt_with_history(history, raw_prompt)
        chat = _build_chat_session(client, session_data)

        try:
            output = await client.generate_content(
                prompt=prompt, model=resolved_model, chat=chat
            )
        except Exception as e:
            err_str = str(e)
            if attempt == 0 and _has_provider_session(session_data):
                logger.warning("Gemini session error, resetting: %s", err_str)
                adapter.clear_provider_session(session_data)
                continue
            return JSONResponse({"error": err_str}, status_code=500)

        # Extract session data
        session_data.update(adapter.extract(chat, session_data))
        session_data["gemini_metadata"] = chat.metadata

        content = output.text or ""
        thoughts = output.thoughts or ""

        append_assistant_message(session_data, content)

        response_data = {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": resolved_model,
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

        if thoughts:
            response_data["choices"][0]["message"]["reasoning_content"] = thoughts

        return JSONResponse(response_data)

    return JSONResponse({"error": "Failed after retry"}, status_code=500)


async def _stream_gemini(
    client: GeminiClient,
    raw_prompt: str,
    resolved_model: str,
    session_data: dict,
    adapter,
    history: list[dict],
) -> AsyncGenerator[str, None]:
    response_id = f"chatcmpl-{int(time.time())}"

    for attempt in range(2):
        has_session = _has_provider_session(session_data) and attempt == 0
        prompt = raw_prompt if has_session else format_prompt_with_history(history, raw_prompt)
        chat = _build_chat_session(client, session_data)

        first = True
        collected = []
        session_error = False

        try:
            gen = client.generate_content_stream(prompt=prompt, model=resolved_model, chat=chat)
            async for chunk in gen:
                delta = chunk.text_delta
                if delta:
                    collected.append(delta)
                    yield make_stream_chunk(resolved_model, delta, response_id, is_first=first)
                    first = False
        except Exception as e:
            err_str = str(e)
            if attempt == 0 and _has_provider_session(session_data):
                logger.warning("Gemini stream session error, resetting: %s", err_str)
                adapter.clear_provider_session(session_data)
                session_error = True
            else:
                yield make_error_chunk(err_str)
                yield STREAM_END
                return

        if session_error:
            continue  # retry with fresh session + history transcript

        # Success
        if not first:
            yield make_stream_chunk(resolved_model, "", response_id, is_final=True)

        session_data.update(adapter.extract(chat, session_data))
        session_data["gemini_metadata"] = chat.metadata
        full_text = "".join(collected)
        append_assistant_message(session_data, full_text)

        yield STREAM_END
        return

    yield make_error_chunk("Gemini session failed after retry")
    yield STREAM_END
