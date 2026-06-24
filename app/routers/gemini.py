import os
import sys
import json
import time
import asyncio
from typing import AsyncGenerator

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Gemini-API/src"))

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from gemini_webapi import GeminiClient
from gemini_webapi.constants import Model as GeminiModel

router = APIRouter()


def _build_model_list(client: GeminiClient | None) -> list[dict]:
    known_names = set()
    models = []

    for member in GeminiModel:
        if member is GeminiModel.UNSPECIFIED:
            continue
        name = member.model_name
        if name not in known_names:
            known_names.add(name)
            display = name.replace("gemini-", "").replace("-", " ").title()
            models.append({
                "id": name,
                "object": "model",
                "created": 1704067200,
                "owned_by": "gemini",
                "description": f"Gemini {display}",
            })

    if client:
        avail = client.list_models()
        if avail:
            for m in avail:
                mid = m.model_name or m.model_id
                if mid and mid not in known_names:
                    known_names.add(mid)
                    models.append({
                        "id": mid,
                        "object": "model",
                        "created": 1704067200,
                        "owned_by": "gemini",
                        "description": m.description or f"Gemini {m.display_name}",
                    })

    return models


def _resolve_model_name(model: str) -> str:
    model_lower = model.lower()
    if model_lower.startswith("gemini-"):
        model_lower = model_lower[7:]
    for member in GeminiModel:
        if member is GeminiModel.UNSPECIFIED:
            continue
        if member.model_name == model or member.model_name == f"gemini-{model_lower}":
            return member.model_name
        if member.name.lower().replace("_", "-") == model_lower:
            return member.model_name
    return model


@router.get("/models")
async def list_models(request: Request):
    client: GeminiClient | None = getattr(request.app.state, "gemini_client", None)
    models = _build_model_list(client)
    return {"object": "list", "data": models}


@router.post("/chat/completions")
async def chat_completions(request: Request):
    client: GeminiClient | None = getattr(request.app.state, "gemini_client", None)
    if not client:
        return JSONResponse(
            {"error": "Gemini client not initialized. Check credentials."},
            status_code=503,
        )

    body = await request.json()
    messages = body.get("messages", [])
    stream = body.get("stream", False)
    model = body.get("model", "gemini-2-0-flash")

    resolved_model = _resolve_model_name(model)

    prompt = messages[-1]["content"] if messages else ""

    if stream:
        return StreamingResponse(
            _stream_gemini(client, prompt, resolved_model),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    try:
        output = await client.generate_content(prompt=prompt, model=resolved_model)
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
                "message": {
                    "role": "assistant",
                    "content": content,
                },
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
        async for chunk in client.generate_content_stream(prompt=prompt, model=resolved_model):
            delta = chunk.text_delta
            if delta:
                data = json.dumps({"choices": [{"delta": {"content": delta}}]})
                yield f"data: {data}\n\n"
    except Exception as e:
        data = json.dumps({"error": str(e)})
        yield f"data: {data}\n\n"
    yield "data: [DONE]\n\n"
