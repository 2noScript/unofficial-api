import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "Gemini-API/src"))

from fastapi import Request
from fastapi.responses import JSONResponse
from gemini_webapi import GeminiClient
from gemini_webapi.constants import Model as GeminiModel


def _get_client(request: Request) -> GeminiClient | None:
    return getattr(request.app.state, "gemini_client", None)


def _require_client(request: Request) -> GeminiClient | JSONResponse | None:
    client = _get_client(request)
    if not client:
        return JSONResponse(
            {"error": "Gemini client not initialized. Check credentials."},
            status_code=503,
        )
    return client


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
