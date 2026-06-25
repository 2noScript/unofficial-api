import json
import time
from typing import AsyncGenerator

from fastapi import Request, Body
from fastapi.responses import JSONResponse, StreamingResponse
from gemini_webapi import GeminiClient

from .router import router
from .helpers import _require_client, _resolve_model_name
from core.schemas import ChatCompletionRequest, ChatCompletionResponse


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
    prompt = messages[-1]["content"] if messages else ""

    if stream:
        return StreamingResponse(
            _stream_gemini(client, prompt, resolved_model),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    try:
        output = await client.generate_content(
            prompt=prompt, model=resolved_model
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

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
    client: GeminiClient, prompt: str, resolved_model: str
) -> AsyncGenerator[str, None]:
    try:
        gen = client.generate_content_stream(prompt=prompt, model=resolved_model)
        async for chunk in gen:
            delta = chunk.text_delta
            if delta:
                data = json.dumps({"choices": [{"delta": {"content": delta}}]})
                yield f"data: {data}\n\n"
    except Exception as e:
        data = json.dumps({"error": str(e)})
        yield f"data: {data}\n\n"
    yield "data: [DONE]\n\n"
