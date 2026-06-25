from fastapi import Request
from notebooklm import NotebookLMClient
from notebooklm.types import Artifact, GenerationStatus

from core.schemas import (
    NLMArtifactResponse,
    NLMGenerationStatusResponse,
)


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


def _artifact_to_response(art: Artifact) -> NLMArtifactResponse:
    return NLMArtifactResponse(
        id=art.id,
        title=art.title or "",
        kind=art.kind.value if hasattr(art.kind, "value") else str(art.kind),
        status=art.status,
        status_str=art.status_str,
        created_at=art.created_at.isoformat() if art.created_at else None,
        url=art.url,
        report_subtype=art.report_subtype if hasattr(art, "report_subtype") else None,
    )


def _generation_status_to_response(gs: GenerationStatus) -> NLMGenerationStatusResponse:
    return NLMGenerationStatusResponse(
        task_id=gs.task_id,
        status=str(gs.status),
        url=gs.url,
        error=gs.error,
        error_code=gs.error_code,
    )
