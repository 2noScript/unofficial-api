import os
import time
import asyncio
import logging
import functools
from typing import AsyncGenerator

from fastapi import APIRouter, Request, Body
from fastapi.responses import JSONResponse, StreamingResponse
from grok_api import Grok, GROK_MODELS, GROK_MODEL_CONFIG

from core.schemas import ChatCompletionRequest, ChatCompletionResponse
from core.stream import make_stream_chunk, make_error_chunk, STREAM_END
from core.utils import extract_text
from core.session.history import sync_and_get_history, append_assistant_message, format_prompt_with_history

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Grok"])


_cached_client: Grok | None = None
_cached_cookie: str = ""


def _get_client() -> Grok | None:
    import dotenv
    dotenv.load_dotenv(override=True)
    cookie_str = os.environ.get("GROK_COOKIE", "").strip().strip("'").strip('"')
    if not cookie_str:
        return None
    return Grok(cookie=cookie_str)


@router.get(
    "/models",
    summary="List available Grok models",
)
async def list_models():
    return {"object": "list", "data": GROK_MODELS}


def _extract_msg_content(msg: any) -> str:
    if isinstance(msg, dict):
        return msg.get("content", "")
    return getattr(msg, "content", "")


def _run_chat(messages: list, model: str, session_data: dict, client: Grok) -> dict:
    user_message = extract_text(_extract_msg_content(messages[-1])) if messages else ""
    history = session_data.get("history", [])
    prompt = format_prompt_with_history(history, user_message)

    session = client.new_session(
        conversation_id=session_data.get("grok_conversation_id"),
        parent_response_id=session_data.get("grok_parent_response_id"),
    )
    result = session.send_message(prompt, model=model)
    if not result.get("ok"):
        raise RuntimeError(result.get("content", "Unknown error"))

    session_data["grok_conversation_id"] = result.get("conversation_id")
    session_data["grok_parent_response_id"] = result.get("parent_response_id")

    content = result.get("content", "")
    append_assistant_message(session_data, content)
    return {"response": content, "thought": result.get("thought", "")}


async def _stream_chat_real(
    messages: list, model: str, session_data: dict, client: Grok
) -> AsyncGenerator[str, None]:
    try:
        user_message = extract_text(_extract_msg_content(messages[-1])) if messages else ""
        history = session_data.get("history", [])
        prompt = format_prompt_with_history(history, user_message)
        response_id = f"chatcmpl-{int(time.time())}"

        print(f"\n==================== [GROK SERVER LIVE REQUEST] ====================", flush=True)
        print(f"[GROK INCOMING PROMPT]: {prompt!r}", flush=True)

        session = client.new_session(
            conversation_id=session_data.get("grok_conversation_id"),
            parent_response_id=session_data.get("grok_parent_response_id"),
        )

        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def run_producer():
            try:
                print(f"[GROK PRODUCER THREAD] Starting websocket stream for prompt: {prompt!r}", flush=True)
                for event_type, content in session.send_message_stream(prompt, model=model):
                    print(f"[GROK PRODUCER EVENT]: {event_type} | {content!r}", flush=True)
                    if event_type == "error":
                        loop.call_soon_threadsafe(queue.put_nowait, ("error", content))
                        return
                    elif event_type in ("content", "thought"):
                        loop.call_soon_threadsafe(queue.put_nowait, ("content", content))

                session_data["grok_conversation_id"] = session.conversation_id
                session_data["grok_parent_response_id"] = session.parent_response_id
                print(f"[GROK PRODUCER THREAD] Websocket stream completed successfully.", flush=True)
                loop.call_soon_threadsafe(queue.put_nowait, ("done", None))
            except Exception as e:
                print(f"[GROK PRODUCER EXCEPTION]: {e!r}", flush=True)
                loop.call_soon_threadsafe(queue.put_nowait, ("error", str(e)))

        loop.run_in_executor(None, run_producer)

        collected_text = []
        first = True

        while True:
            item_type, content = await queue.get()
            if item_type == "error":
                print(f"[GROK SERVER ERROR]: {content!r}", flush=True)
                print(f"===================================================================\n", flush=True)
                yield make_error_chunk(content or "Stream error")
                yield STREAM_END
                return
            elif item_type == "done":
                full_response = "".join(collected_text)
                append_assistant_message(session_data, full_response)
                print(f"[GROK SERVER FULL RESPONSE]: {full_response!r}", flush=True)
                print(f"==================== [GROK SERVER COMPLETED] ====================\n", flush=True)
                yield make_stream_chunk(model, "", response_id, is_final=True)
                yield STREAM_END
                return
            elif item_type == "content":
                collected_text.append(content)
                print(f"[GROK STREAM CHUNK]: {content!r}", flush=True)
                yield make_stream_chunk(model, content, response_id, is_first=first)
                first = False

    except Exception as e:
        logger.error("Grok streaming failed: %s", e)
        print(f"[GROK EXCEPTION]: {e}", flush=True)
        yield make_error_chunk(str(e))
        yield STREAM_END


@router.post(
    "/chat/completions",
    summary="Create a chat completion using Grok models",
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
                    "stream": False,
                },
            }
        }
    ),
):
    client = _get_client()
    if not client:
        return JSONResponse(
            {"error": "Grok client not initialized. Set GROK_COOKIE in .env."},
            status_code=503,
        )

    model = body.model or "grok-3"
    if model.lower() not in GROK_MODEL_CONFIG:
        return JSONResponse(
            {
                "error": {
                    "message": f"Model '{model}' not supported. Supported: {list(GROK_MODEL_CONFIG)}",
                    "type": "invalid_request_error",
                    "code": "model_not_found",
                }
            },
            status_code=400,
        )

    messages = [m.model_dump() for m in body.messages]
    stream = body.stream
    session_data = getattr(request.state, "session_data", {})
    sync_and_get_history(messages, session_data)

    try:
        if stream:
            return StreamingResponse(
                _stream_chat_real(body.messages, model, session_data, client),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
            )

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, functools.partial(_run_chat, body.messages, model, session_data, client)
        )
        content_text = result.get("response", "")
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content_text},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": len(content_text.split()) if content_text else 0,
                "total_tokens": len(content_text.split()) if content_text else 0,
            },
        }
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
