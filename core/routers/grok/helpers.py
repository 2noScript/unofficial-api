from fastapi import Request
from app.control.model.registry import list_by_capability
from app.control.model.enums import Capability

from .client import GrokClient


GROK_MODELS = [
    {
        "id": m.model_name,
        "object": "model",
        "created": 1704067200,
        "owned_by": "xai",
        "description": m.public_name,
    }
    for m in list_by_capability(Capability.CHAT)
]


def resolve_model(model_name: str) -> str | None:
    from app.control.model.registry import get
    spec = get(model_name)
    return spec.model_name if spec else None


def get_client(request: Request) -> GrokClient | None:
    return getattr(request.app.state, "grok_client", None)
