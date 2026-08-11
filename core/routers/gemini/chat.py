import json
import time
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

from fastapi import Request, Body
from fastapi.responses import JSONResponse, StreamingResponse
from gemini_webapi import GeminiClient, ChatSession
from gemini_webapi.constants import Model as GeminiModel

from .router import router
from .helpers import _require_client, _resolve_model_name
from core.schemas import ChatCompletionRequest, ChatCompletionResponse
from core.utils import extract_text, make_stream_chunk, make_error_chunk, STREAM_END
from core.session.adapters import get_adapter
from core.session.history import sync_and_get_history, append_assistant_message, format_prompt_with_history
from core.load_balancer import load_balancer, NoActiveProfileError
from .pool import gemini_pool


def _build_chat_session(client: GeminiClient, session_data: dict) -> ChatSession:
    """Create a ChatSession from stored session state using GeminiAdapter."""
    adapter = get_adapter("gemini")
    chat = adapter.inject(session_data, {"client": client, "chat_cls": ChatSession}).get("chat")
    if chat:
        return chat
    return ChatSession(geminiclient=client)


def _has_provider_session(session_data: dict) -> bool:
    cid = session_data.get("gemini_cid")
    if cid:
        return True
    metadata = session_data.get("gemini_metadata")
    if metadata and isinstance(metadata, list) and len(metadata) > 0 and bool(metadata[0]):
        return True
    return False


async def _resolve_gemini_client(request: Request, session_data: dict) -> tuple[GeminiClient | None, str | None, JSONResponse | None]:
    """Resolve an active Gemini client from load balancer profiles or fallback env."""
    active_profiles = load_balancer.get_active_profiles("gemini")
    max_attempts = max(1, len(active_profiles))

    for attempt in range(max_attempts):
        profile_id = None
        try:
            profile, _ = load_balancer.select_profile("gemini", session_data=session_data)
            profile_id = profile.get("id")
            client = await gemini_pool.get_or_create_client(profile)
            return client, profile_id, None
        except NoActiveProfileError:
            client = _require_client(request)
            if isinstance(client, JSONResponse):
                return None, None, client
            return client, None, None
        except Exception as e:
            err_str = str(e)
            logger.warning("Gemini profile '%s' init failed (%s). Failing over...", profile_id, err_str)
            if profile_id and load_balancer.is_retryable_error(err_str):
                load_balancer.handle_profile_failure(profile_id, session_data)
                if profile_id in gemini_pool._clients:
                    del gemini_pool._clients[profile_id]
            if attempt < max_attempts - 1 and load_balancer.get_active_profiles("gemini"):
                continue
            return None, None, JSONResponse(
                {"error": {"message": f"Gemini profile error: {str(e)}", "type": "server_error", "code": "upstream_error"}},
                status_code=500,
            )
    return None, None, JSONResponse(
        {"error": {"message": "No active Gemini profile available.", "type": "server_error", "code": "no_active_profile"}},
        status_code=503,
    )


from core.services.chat_service import chat_service
from core.services.gemini_strategy import GeminiStrategy

gemini_strategy = GeminiStrategy()


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
    session_data = getattr(request.state, "session_data", {})
    VALID_GEMINI_MODELS = {m.model_name for m in GeminiModel if m is not GeminiModel.UNSPECIFIED}

    messages = [m.model_dump() for m in body.messages]
    stream = body.stream
    model = body.model or "gemini-3-flash"

    resolved_model = _resolve_model_name(model)
    if resolved_model not in VALID_GEMINI_MODELS:
        return JSONResponse(
            {"error": {"message": f"Model '{model}' not supported. Supported: {sorted(VALID_GEMINI_MODELS)}", "type": "invalid_request_error", "code": "model_not_found"}},
            status_code=400,
        )

    raw_prompt = extract_text(messages[-1].get("content")) if messages else ""
    logger.info("Request /v1/gemini/chat/completions: %s", body.model_dump_json())

    adapter = get_adapter("gemini")
    sync_and_get_history(messages, session_data)
    history = session_data.get("history", [])

    if stream:
        client, profile_id, err_response = await chat_service.resolve_client(gemini_strategy, request, session_data)
        if err_response or not client:
            return err_response or JSONResponse({"error": {"message": "Gemini client not available", "type": "server_error", "code": "upstream_error"}}, status_code=503)
        return StreamingResponse(
            _stream_gemini(client, raw_prompt, resolved_model, session_data, adapter, history, profile_id),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    return await chat_service.execute_chat(
        strategy=gemini_strategy,
        request=request,
        messages=messages,
        model=resolved_model,
        session_data=session_data,
        adapter=adapter,
    )


async def _stream_gemini(
    client: GeminiClient,
    raw_prompt: str,
    resolved_model: str,
    session_data: dict,
    adapter,
    history: list[dict],
    profile_id: str | None = None,
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
            if load_balancer.is_retryable_error(err_str):
                if profile_id:
                    load_balancer.handle_profile_failure(profile_id, session_data)

            if attempt == 0 and _has_provider_session(session_data) and first:
                logger.warning("Gemini stream session error, resetting: %s", err_str)
                adapter.clear_provider_session(session_data)
                session_error = True
            else:
                logger.error("Gemini stream error: %s", err_str)
                yield make_error_chunk(err_str)
                yield STREAM_END
                return

        if session_error:
            continue  # retry with fresh session + history transcript

        # Success
        if not first:
            yield make_stream_chunk(resolved_model, "", response_id, is_final=True)

        session_data.update(adapter.extract(chat, session_data))
        full_text = "".join(collected)
        append_assistant_message(session_data, full_text)

        yield STREAM_END
        return

    yield make_error_chunk("Gemini session failed after retry")
    yield STREAM_END
