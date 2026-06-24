import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "GrokWeb-to-API"))

from fastapi import Request
from grok_client import GrokClient


_executor = ThreadPoolExecutor(max_workers=4)

GROK_MODELS = [
    {
        "id": "grok-3",
        "object": "model",
        "created": 1704067200,
        "owned_by": "xai",
        "description": "Grok 3 — chat with optional web search, powered by xAI",
    },
]


def get_client(request: Request) -> GrokClient | None:
    return getattr(request.app.state, "grok_client", None)
