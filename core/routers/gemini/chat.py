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
    )
):
    client = _require_client(request)
    if isinstance(client, JSONResponse):
        return client

    messages = [m.model_dump() for m in body.messages]
    stream = body.stream
    model = body.model or "gemini-3-flash"

    resolved_model = _resolve_model_name(model)
    prompt = extract_text(messages[-1].get("content")) if messages else ""
    logger.info("Request /v1/gemini/chat/completions: %s", body.model_dump_json())

    # Session integration
    adapter = get_adapter("gemini")
    session_data = getattr(request.state, "session_data", {})
    session_args = adapter.inject(session_data, {})
    
    metadata = session_data.get("gemini_metadata")
    if metadata:
        chat = ChatSession(geminiclient=client, metadata=metadata)
    else:
        cid = session_args.get("chat_data", {}).get("cid") if "chat_data" in session_args else None
        chat = ChatSession(geminiclient=client, cid=cid or "")

    if stream:
        return StreamingResponse(
            _stream_gemini(client, prompt, resolved_model, chat, session_data, adapter),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    try:
        output = await client.generate_content(
            prompt=prompt, model=resolved_model, chat=chat
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    # Extract session data
    session_data.update(adapter.extract(chat, session_data))
    session_data["gemini_metadata"] = chat.metadata

    content = output.text or ""
    thoughts = output.thoughts or ""

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


async def _stream_gemini(
    client: GeminiClient, prompt: str, resolved_model: str, chat: ChatSession, session_data: dict, adapter
) -> AsyncGenerator[str, None]:
    response_id = f"chatcmpl-{int(time.time())}"
    first = True
    try:
        gen = client.generate_content_stream(prompt=prompt, model=resolved_model, chat=chat)
        async for chunk in gen:
            delta = chunk.text_delta
            if delta:
                yield make_stream_chunk(resolved_model, delta, response_id, is_first=first)
                first = False
        if not first:
            yield make_stream_chunk(resolved_model, "", response_id, is_final=True)
        # Extract session data after successful stream completion
        session_data.update(adapter.extract(chat, session_data))
        session_data["gemini_metadata"] = chat.metadata
        yield STREAM_END
    except Exception as e:
        yield make_error_chunk(str(e))
        yield STREAM_END
