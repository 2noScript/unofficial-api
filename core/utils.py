import os
import re
import json
import time
from typing import Any



def parse_cookie(cookie_str: str | None, name: str) -> str | None:
    if not cookie_str:
        return None
    m = re.search(rf"(?:^|;\s*){re.escape(name)}=([^;]+)", cookie_str)
    return m.group(1) if m else None


def extract_text(content: str | list | None) -> str:
    if not content:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                t = part.get("text", "")
                if t:
                    texts.append(t)
        return " ".join(texts)
    return str(content)


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






