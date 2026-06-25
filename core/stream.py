import json
import time


def make_stream_chunk(
    model: str,
    content: str,
    response_id: str,
    *,
    is_first: bool = False,
    is_final: bool = False,
) -> str:
    delta = {}
    if is_first:
        delta["role"] = "assistant"
    if content:
        delta["content"] = content

    choice = {"index": 0, "delta": delta}
    if is_final:
        choice["finish_reason"] = "stop"
    else:
        choice["finish_reason"] = None

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
