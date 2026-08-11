import json
import time
from typing import Any


def make_stream_chunk(
    model: str,
    content: str,
    response_id: str,
    *,
    is_first: bool = False,
    is_final: bool = False,
) -> str:
    delta: dict[str, str] = {}
    if is_first:
        delta["role"] = "assistant"
    if content:
        delta["content"] = content

    choice: dict[str, Any] = {
        "index": 0,
        "delta": delta,
        "finish_reason": "stop" if is_final else None,
    }

    chunk = {
        "id": response_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [choice],
    }
    return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"


def make_error_chunk(error_msg: str, error_type: str = "server_error", code: str = "") -> str:
    data = json.dumps({
        "error": {
            "message": error_msg,
            "type": error_type,
            "code": code,
        }
    }, ensure_ascii=False)
    return f"data: {data}\n\n"


STREAM_END = "data: [DONE]\n\n"
