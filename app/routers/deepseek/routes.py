import os
import sys
import json
import time
import asyncio
from io import StringIO
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncGenerator

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "deepseek-api"))

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from DeepSeekAPI import DeepSeekChat
from app.schemas import ChatCompletionRequest, ChatCompletionResponse, ModelList, ModelObject

router = APIRouter(tags=["DeepSeek"])
_executor = ThreadPoolExecutor(max_workers=4)

DEEPSEEK_MODELS = [
    {
        "id": "deepseek-v3",
        "object": "model",
        "created": 1704067200,
        "owned_by": "deepseek",
        "description": "DeepSeek V3 - Fast responses without extended thinking",
    },
    {
        "id": "deepseek-r1",
        "object": "model",
        "created": 1704067200,
        "owned_by": "deepseek",
        "description": "DeepSeek R1 - Reasoning model with extended thinking",
    },
    {
        "id": "deepseek-v4",
        "object": "model",
        "created": 1704067200,
        "owned_by": "deepseek",
        "description": "DeepSeek V4 - Expert model without extended thinking",
    },
    {
        "id": "deepseek-r4",
        "object": "model",
        "created": 1704067200,
        "owned_by": "deepseek",
        "description": "DeepSeek R4 - Expert reasoning model with extended thinking",
    },
]


def _get_auth():
    ds_session_id = os.environ.get("DEEPSEEK_SESSION_ID") or os.environ.get("DS_SESSION_ID")
    auth_token = os.environ.get("DEEPSEEK_AUTH_TOKEN") or os.environ.get("AUTHORIZATION_TOKEN")
    if not ds_session_id or not auth_token:
        raise ValueError(
            "DeepSeek credentials not found. Set DEEPSEEK_SESSION_ID and DEEPSEEK_AUTH_TOKEN"
        )
    return ds_session_id, auth_token


def _get_model_config(model: str):
    model_lower = model.lower()
    model_type = "default"
    thinking_enabled = "r1" in model_lower or "r4" in model_lower or "reasoning" in model_lower or "reasoner" in model_lower
    return model_type, thinking_enabled


def _run_chat(messages: list, model_type: str, thinking_enabled: bool) -> str:
    ds_session_id, auth_token = _get_auth()
    user_message = messages[-1]["content"] if messages else ""

    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()
    try:
        chat = DeepSeekChat(ds_session_id, auth_token)
        chat.send_message(
            user_message,
            printing=True,
            thinking_enabled=thinking_enabled,
            search_enabled=False,
            model_type=model_type,
        )
    finally:
        sys.stdout = old_stdout

    output = mystdout.getvalue()

    in_response = False
    response_text = ""
    for line in output.split("\n"):
        if "START RESPONSE" in line:
            in_response = True
            continue
        elif "FINISHED" in line:
            break
        elif "START THINK" in line:
            in_response = False
            continue
        if in_response and line.strip():
            response_text += line + "\n"

    return response_text.strip() if response_text else output.strip()


def _run_chat_and_get_lines(messages: list, model_type: str, thinking_enabled: bool) -> list[str]:
    ds_session_id, auth_token = _get_auth()
    user_message = messages[-1]["content"] if messages else ""

    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()
    try:
        chat = DeepSeekChat(ds_session_id, auth_token)
        chat.send_message(
            user_message,
            printing=True,
            thinking_enabled=thinking_enabled,
            search_enabled=False,
            model_type=model_type,
        )
    finally:
        sys.stdout = old_stdout

    output = mystdout.getvalue()
    lines = []
    in_response = False
    for line in output.split("\n"):
        if "START RESPONSE" in line:
            in_response = True
            continue
        elif "FINISHED" in line:
            break
        elif "START THINK" in line:
            in_response = False
            continue
        if in_response and line.strip():
            lines.append(line + "\n")
    return lines


async def _stream_chat(messages: list, model_type: str, thinking_enabled: bool) -> AsyncGenerator[str, None]:
    try:
        loop = asyncio.get_event_loop()
        lines = await loop.run_in_executor(
            _executor, _run_chat_and_get_lines, messages, model_type, thinking_enabled
        )
        for line in lines:
            chunk = json.dumps({"choices": [{"delta": {"content": line}}]})
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
    except ValueError as e:
        data = json.dumps({"error": str(e)})
        yield f"data: {data}\n\n"
    except Exception as e:
        data = json.dumps({"error": str(e)})
        yield f"data: {data}\n\n"


@router.get(
    "/models",
    summary="List available DeepSeek models",
    response_model=ModelList,
)
def list_models():
    return {"object": "list", "data": DEEPSEEK_MODELS}


@router.post(
    "/chat/completions",
    summary="Create a chat completion using DeepSeek models",
    response_model=ChatCompletionResponse,
)
async def chat_completions(body: ChatCompletionRequest):
    messages = [m.model_dump() for m in body.messages]
    stream = body.stream
    model = body.model or "deepseek-v3"

    model_type, thinking_enabled = _get_model_config(model)

    try:
        if stream:
            return StreamingResponse(
                _stream_chat(messages, model_type, thinking_enabled),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor, _run_chat, messages, model_type, thinking_enabled
        )
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=401)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    return JSONResponse({
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": result},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": len(result.split()) if result else 0,
            "total_tokens": len(result.split()) if result else 0,
        },
    })
