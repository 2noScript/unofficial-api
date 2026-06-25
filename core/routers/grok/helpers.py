from fastapi import Request
from .client import GrokClient


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
