from fastapi import Request
from notebooklm import NotebookLMClient


def _build_model_list() -> list[dict]:
    return [
        {
            "id": "notebooklm-2-0",
            "object": "model",
            "created": 1704067200,
            "owned_by": "google",
            "description": "NotebookLM - Source-grounded Q&A with Google's Gemini models",
        },
    ]


async def _get_client(request: Request) -> NotebookLMClient | None:
    return getattr(request.app.state, "notebooklm_client", None)


async def _require_client(request: Request) -> NotebookLMClient:
    client = await _get_client(request)
    if not client:
        raise ValueError("NotebookLM client not initialized. Login via `notebooklm login` first.")
    return client
