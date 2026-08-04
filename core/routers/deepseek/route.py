import os
import json
import logging
import httpx

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse, StreamingResponse
from core.schemas import ChatCompletionRequest, ChatCompletionResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["DeepSeek"])

DS_FREE_API_URL = os.environ.get("DS_FREE_API_URL", "http://127.0.0.1:22217")
DS_FREE_API_KEY = os.environ.get("DS_FREE_API_KEY", "")

DEEPSEEK_MODEL_CONFIG = {
    "deepseek-v3": "deepseek-default",
    "deepseek-r1": "deepseek-default",
    "deepseek-v4": "deepseek-default",
    "deepseek-r4": "deepseek-default",
    "deepseek-default": "deepseek-default",
    "deepseek-expert": "deepseek-expert",
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
    model = (body.model or "deepseek-v3").lower()
    if model not in DEEPSEEK_MODEL_CONFIG:
        return JSONResponse(
            {"error": {"message": f"Model '{model}' not supported. Supported: {list(DEEPSEEK_MODEL_CONFIG)}", "type": "invalid_request_error", "code": "model_not_found"}},
            status_code=400,
        )

    target_url = f"{DS_FREE_API_URL.rstrip('/')}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    if DS_FREE_API_KEY:
        headers["Authorization"] = f"Bearer {DS_FREE_API_KEY}"

    payload = body.model_dump(exclude_none=True)
    payload["model"] = DEEPSEEK_MODEL_CONFIG.get(model, "deepseek-default")

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            if body.stream:
                async def stream_gen():
                    try:
                        async with client.stream("POST", target_url, headers=headers, json=payload) as response:
                            async for line in response.aiter_lines():
                                if line:
                                    yield f"{line}\n\n"
                    except Exception as e:
                        yield f"data: {json.dumps({'error': {'message': str(e), 'type': 'server_error', 'code': 'upstream_error'}})}\n\n"
                        yield "data: [DONE]\n\n"

                return StreamingResponse(
                    stream_gen(),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
                )
            else:
                resp = await client.post(target_url, headers=headers, json=payload)
                return JSONResponse(status_code=resp.status_code, content=resp.json())
    except Exception as e:
        return JSONResponse(
            {"error": {"message": str(e), "type": "server_error", "code": "upstream_error"}},
            status_code=500,
        )
