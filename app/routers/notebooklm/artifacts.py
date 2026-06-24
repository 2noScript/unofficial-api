import csv
import io
import json
import logging
import re
import html as html_mod
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from notebooklm import NotebookLMClient
from notebooklm._artifact.listing import ArtifactListingService
from notebooklm._note_service import NoteService
from notebooklm._mind_map import NoteBackedMindMapService
from notebooklm._mind_maps_api import extract_interactive_tree_leaf, _parse_tree
from notebooklm._row_adapters.artifacts import ArtifactRow
from notebooklm.rpc import RPCMethod, safe_index
from notebooklm.rpc.types import (
    ArtifactTypeCode,
    AudioFormat,
    AudioLength,
    InfographicDetail,
    InfographicOrientation,
    InfographicStyle,
    QuizDifficulty,
    QuizQuantity,
    ReportFormat,
    SlideDeckFormat,
    SlideDeckLength,
    VideoFormat,
    VideoStyle,
)
from notebooklm.types import ArtifactType

from app.schemas import (
    NLMArtifactDownloadUrlResponse,
    NLMArtifactListResponse,
    NLMArtifactResponse,
    NLMAudioGenerateRequest,
    NLMDataTableGenerateRequest,
    NLMExportRequest,
    NLMGenerateRequest,
    NLMGenerationStatusResponse,
    NLMInfographicGenerateRequest,
    NLMMindMapGenerateRequest,
    NLMQuizFlashcardsGenerateRequest,
    NLMRenameRequest,
    NLMReportGenerateRequest,
    NLMReportSuggestionListResponse,
    NLMReportSuggestionResponse,
    NLMReviseSlideRequest,
    NLMSlideDeckGenerateRequest,
    NLMStudyGuideGenerateRequest,
    NLMVideoGenerateRequest,
    NLMWaitRequest,
)

from .helpers import (
    _artifact_to_response,
    _generation_status_to_response,
    _require_client,
)
from .router import router

logger = logging.getLogger(__name__)


async def _list_raw(client: NotebookLMClient, notebook_id: str) -> list[Any]:
    listing = ArtifactListingService()
    return await listing.list_raw(notebook_id, rpc=client._rpc_executor)


async def _resolve_source_ids(client: NotebookLMClient, notebook_id: str, source_ids: list[str] | None) -> list[str]:
    if source_ids is not None:
        return source_ids
    return await client.notebooks.get_source_ids(notebook_id)


def _extract_app_data(html_content: str) -> dict | None:
    """Extract JSON from data-app-data HTML attribute (quiz/flashcard)."""
    match = re.search(r'data-app-data="([^"]+)"', html_content)
    if not match:
        return None
    encoded_json = match.group(1)
    decoded_json = html_mod.unescape(encoded_json)
    try:
        return json.loads(decoded_json)
    except json.JSONDecodeError:
        return None


def _parse_data_table_csv(payload: Any) -> str | None:
    """Parse data table raw payload into CSV string."""
    try:
        from notebooklm._artifact.formatters import _parse_data_table
        headers, rows = _parse_data_table(payload)
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(headers)
        writer.writerows(rows)
        return buf.getvalue()
    except Exception:
        return None


# ─────────────────────────────────────────────
# List / Get
# ─────────────────────────────────────────────


@router.get("/notebooks/{notebook_id}/artifacts", summary="List artifacts in a notebook")
async def list_artifacts(notebook_id: str, request: Request, type: str | None = None):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    artifact_type = None
    if type:
        try:
            artifact_type = ArtifactType(type)
        except ValueError:
            return JSONResponse({"error": f"Invalid artifact type: {type}"}, status_code=400)

    try:
        artifacts = await client.artifacts.list(notebook_id, artifact_type)
        return NLMArtifactListResponse(
            data=[_artifact_to_response(a) for a in artifacts]
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/notebooks/{notebook_id}/artifacts/{artifact_id}", summary="Get a specific artifact")
async def get_artifact(notebook_id: str, artifact_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        art = await client.artifacts.get(notebook_id, artifact_id)
        return _artifact_to_response(art)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/notebooks/{notebook_id}/artifacts/{artifact_id}/prompt",
    summary="Get an artifact's generation prompt",
)
async def get_artifact_prompt(notebook_id: str, artifact_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        prompt = await client.artifacts.get_prompt(notebook_id, artifact_id)
        return {"prompt": prompt}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ─────────────────────────────────────────────
# Generate endpoints
# ─────────────────────────────────────────────


@router.post(
    "/notebooks/{notebook_id}/artifacts/generate/audio",
    summary="Generate an Audio Overview (podcast)",
    status_code=201,
)
async def generate_audio(notebook_id: str, body: NLMAudioGenerateRequest, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    audio_format = AudioFormat[body.audio_format.upper()] if body.audio_format else None
    audio_length = AudioLength[body.audio_length.upper()] if body.audio_length else None

    try:
        source_ids = await _resolve_source_ids(client, notebook_id, body.source_ids)
        result = await client.artifacts.generate_audio(
            notebook_id,
            source_ids=source_ids,
            language=body.language,
            instructions=body.instructions,
            audio_format=audio_format,
            audio_length=audio_length,
        )
        return _generation_status_to_response(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/artifacts/generate/video",
    summary="Generate a Video Overview",
    status_code=201,
)
async def generate_video(notebook_id: str, body: NLMVideoGenerateRequest, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    video_format = VideoFormat[body.video_format.upper()] if body.video_format else None
    video_style = VideoStyle[body.video_style.upper()] if body.video_style else None

    try:
        source_ids = await _resolve_source_ids(client, notebook_id, body.source_ids)
        result = await client.artifacts.generate_video(
            notebook_id,
            source_ids=source_ids,
            language=body.language,
            instructions=body.instructions,
            video_format=video_format,
            video_style=video_style,
            style_prompt=body.style_prompt,
        )
        return _generation_status_to_response(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/artifacts/generate/cinematic-video",
    summary="Generate a Cinematic Video Overview",
    status_code=201,
)
async def generate_cinematic_video(notebook_id: str, body: NLMGenerateRequest, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        source_ids = await _resolve_source_ids(client, notebook_id, body.source_ids)
        result = await client.artifacts.generate_cinematic_video(
            notebook_id,
            source_ids=source_ids,
            language=body.language,
            instructions=body.instructions,
        )
        return _generation_status_to_response(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/artifacts/generate/report",
    summary="Generate a Report",
    status_code=201,
)
async def generate_report(notebook_id: str, body: NLMReportGenerateRequest, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        fmt = ReportFormat(body.report_format)
    except ValueError:
        return JSONResponse({"error": f"Invalid report format: {body.report_format}"}, status_code=400)

    try:
        source_ids = await _resolve_source_ids(client, notebook_id, body.source_ids)
        result = await client.artifacts.generate_report(
            notebook_id,
            report_format=fmt,
            source_ids=source_ids,
            language=body.language,
            custom_prompt=body.custom_prompt,
            extra_instructions=body.extra_instructions,
        )
        return _generation_status_to_response(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/artifacts/generate/study-guide",
    summary="Generate a Study Guide",
    status_code=201,
)
async def generate_study_guide(notebook_id: str, body: NLMStudyGuideGenerateRequest, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        source_ids = await _resolve_source_ids(client, notebook_id, body.source_ids)
        result = await client.artifacts.generate_study_guide(
            notebook_id,
            source_ids=source_ids,
            language=body.language,
            extra_instructions=body.extra_instructions,
        )
        return _generation_status_to_response(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/artifacts/generate/quiz",
    summary="Generate a Quiz",
    status_code=201,
)
async def generate_quiz(notebook_id: str, body: NLMQuizFlashcardsGenerateRequest, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    quantity = QuizQuantity[body.quantity.upper()] if body.quantity else None
    difficulty = QuizDifficulty[body.difficulty.upper()] if body.difficulty else None

    try:
        source_ids = await _resolve_source_ids(client, notebook_id, body.source_ids)
        result = await client.artifacts.generate_quiz(
            notebook_id,
            source_ids=source_ids,
            instructions=body.instructions,
            quantity=quantity,
            difficulty=difficulty,
        )
        return _generation_status_to_response(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/artifacts/generate/flashcards",
    summary="Generate Flashcards",
    status_code=201,
)
async def generate_flashcards(notebook_id: str, body: NLMQuizFlashcardsGenerateRequest, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    quantity = QuizQuantity[body.quantity.upper()] if body.quantity else None
    difficulty = QuizDifficulty[body.difficulty.upper()] if body.difficulty else None

    try:
        source_ids = await _resolve_source_ids(client, notebook_id, body.source_ids)
        result = await client.artifacts.generate_flashcards(
            notebook_id,
            source_ids=source_ids,
            instructions=body.instructions,
            quantity=quantity,
            difficulty=difficulty,
        )
        return _generation_status_to_response(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/artifacts/generate/infographic",
    summary="Generate an Infographic",
    status_code=201,
)
async def generate_infographic(notebook_id: str, body: NLMInfographicGenerateRequest, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    orientation = InfographicOrientation[body.orientation.upper()] if body.orientation else None
    detail_level = InfographicDetail[body.detail_level.upper()] if body.detail_level else None
    style = InfographicStyle[body.style.upper()] if body.style else None

    try:
        source_ids = await _resolve_source_ids(client, notebook_id, body.source_ids)
        result = await client.artifacts.generate_infographic(
            notebook_id,
            source_ids=source_ids,
            language=body.language,
            instructions=body.instructions,
            orientation=orientation,
            detail_level=detail_level,
            style=style,
        )
        return _generation_status_to_response(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/artifacts/generate/slide-deck",
    summary="Generate a Slide Deck",
    status_code=201,
)
async def generate_slide_deck(notebook_id: str, body: NLMSlideDeckGenerateRequest, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    slide_format = SlideDeckFormat[body.slide_format.upper()] if body.slide_format else None
    slide_length = SlideDeckLength[body.slide_length.upper()] if body.slide_length else None

    try:
        source_ids = await _resolve_source_ids(client, notebook_id, body.source_ids)
        result = await client.artifacts.generate_slide_deck(
            notebook_id,
            source_ids=source_ids,
            language=body.language,
            instructions=body.instructions,
            slide_format=slide_format,
            slide_length=slide_length,
        )
        return _generation_status_to_response(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/artifacts/generate/data-table",
    summary="Generate a Data Table",
    status_code=201,
)
async def generate_data_table(notebook_id: str, body: NLMDataTableGenerateRequest, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        source_ids = await _resolve_source_ids(client, notebook_id, body.source_ids)
        result = await client.artifacts.generate_data_table(
            notebook_id,
            source_ids=source_ids,
            language=body.language,
            instructions=body.instructions,
        )
        return _generation_status_to_response(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/artifacts/generate/mind-map",
    summary="Generate a Mind Map",
    status_code=201,
)
async def generate_mind_map(notebook_id: str, body: NLMMindMapGenerateRequest, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        source_ids = await _resolve_source_ids(client, notebook_id, body.source_ids)
        result = await client.artifacts.generate_mind_map(
            notebook_id,
            source_ids=source_ids,
            language=body.language,
            instructions=body.instructions,
        )
        return {
            "note_id": result.note_id,
            "mind_map": {
                "id": result.mind_map.id,
                "notebook_id": result.mind_map.notebook_id,
                "title": result.mind_map.title,
                "kind": result.mind_map.kind.value if hasattr(result.mind_map.kind, "value") else str(result.mind_map.kind),
                "created_at": result.mind_map.created_at.isoformat() if result.mind_map.created_at else None,
                "tree": result.mind_map.tree,
            },
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ─────────────────────────────────────────────
# Post-generation actions
# ─────────────────────────────────────────────


@router.post(
    "/notebooks/{notebook_id}/artifacts/{artifact_id}/retry",
    summary="Retry a failed artifact generation",
)
async def retry_artifact(notebook_id: str, artifact_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        result = await client.artifacts.retry_failed(notebook_id, artifact_id)
        return _generation_status_to_response(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/artifacts/{artifact_id}/revise-slide",
    summary="Revise an individual slide",
)
async def revise_slide(notebook_id: str, artifact_id: str, body: NLMReviseSlideRequest, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        result = await client.artifacts.revise_slide(
            notebook_id, artifact_id, body.slide_index, body.prompt
        )
        return _generation_status_to_response(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/notebooks/{notebook_id}/artifacts/{task_id}/status",
    summary="Poll generation status",
)
async def poll_artifact_status(notebook_id: str, task_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        result = await client.artifacts.poll_status(notebook_id, task_id)
        return _generation_status_to_response(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/artifacts/{task_id}/wait",
    summary="Wait for generation to complete (long-poll)",
)
async def wait_artifact_completion(notebook_id: str, task_id: str, body: NLMWaitRequest, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        result = await client.artifacts.wait_for_completion(
            notebook_id,
            task_id,
            timeout=body.timeout,
            initial_interval=body.initial_interval,
            max_interval=body.max_interval,
        )
        return _generation_status_to_response(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/notebooks/{notebook_id}/artifacts/suggest-reports",
    summary="Get AI-suggested report formats",
)
async def suggest_reports(notebook_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        suggestions = await client.artifacts.suggest_reports(notebook_id)
        return NLMReportSuggestionListResponse(
            data=[
                NLMReportSuggestionResponse(
                    title=s.title,
                    description=s.description,
                    prompt=s.prompt,
                )
                for s in suggestions
            ]
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ─────────────────────────────────────────────
# Management
# ─────────────────────────────────────────────


@router.delete(
    "/notebooks/{notebook_id}/artifacts/{artifact_id}",
    summary="Delete an artifact",
)
async def delete_artifact(notebook_id: str, artifact_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        await client.artifacts.delete(notebook_id, artifact_id)
        return {"status": "deleted", "artifact_id": artifact_id}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.patch(
    "/notebooks/{notebook_id}/artifacts/{artifact_id}",
    summary="Rename an artifact",
)
async def rename_artifact(notebook_id: str, artifact_id: str, body: NLMRenameRequest, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        result = await client.artifacts.rename(notebook_id, artifact_id, body.title)
        return _artifact_to_response(result) if result else {"status": "renamed"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ─────────────────────────────────────────────
# Download: media types (return CDN URL)
# ─────────────────────────────────────────────

async def _get_artifact_url_from_raw(
    client: NotebookLMClient, notebook_id: str, artifact_id: str, type_code: ArtifactTypeCode
) -> str | None:
    raw = await _list_raw(client, notebook_id)
    row = ArtifactListingService().select_completed_artifact_row(
        raw, artifact_id, "Artifact", "artifact", type_code=type_code
    )
    return row.artifact_url(type_code.value, suppress_drift=True)


@router.get(
    "/notebooks/{notebook_id}/artifacts/{artifact_id}/download/audio",
    summary="Get Audio Overview download URL",
)
async def download_audio(notebook_id: str, artifact_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)
    try:
        url = await _get_artifact_url_from_raw(client, notebook_id, artifact_id, ArtifactTypeCode.AUDIO)
        return NLMArtifactDownloadUrlResponse(url=url)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/notebooks/{notebook_id}/artifacts/{artifact_id}/download/video",
    summary="Get Video Overview download URL",
)
async def download_video(notebook_id: str, artifact_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)
    try:
        url = await _get_artifact_url_from_raw(client, notebook_id, artifact_id, ArtifactTypeCode.VIDEO)
        return NLMArtifactDownloadUrlResponse(url=url)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/notebooks/{notebook_id}/artifacts/{artifact_id}/download/infographic",
    summary="Get Infographic download URL",
)
async def download_infographic(notebook_id: str, artifact_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)
    try:
        url = await _get_artifact_url_from_raw(client, notebook_id, artifact_id, ArtifactTypeCode.INFOGRAPHIC)
        return NLMArtifactDownloadUrlResponse(url=url)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/notebooks/{notebook_id}/artifacts/{artifact_id}/download/slide-deck",
    summary="Get Slide Deck download URL",
)
async def download_slide_deck(notebook_id: str, artifact_id: str, request: Request, format: str = "pdf"):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)
    try:
        raw = await _list_raw(client, notebook_id)
        row = ArtifactListingService().select_completed_artifact_row(
            raw, artifact_id, "Slide deck", "slide_deck", type_code=ArtifactTypeCode.SLIDE_DECK
        )
        if format == "pptx":
            url = row.slide_deck_pptx_url
        else:
            url = row.slide_deck_pdf_url
        return NLMArtifactDownloadUrlResponse(url=url, format=format)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ─────────────────────────────────────────────
# Download: content types (return inline content)
# ─────────────────────────────────────────────

@router.get(
    "/notebooks/{notebook_id}/artifacts/{artifact_id}/download/report",
    summary="Download report as markdown",
)
async def download_report(notebook_id: str, artifact_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)
    try:
        raw = await _list_raw(client, notebook_id)
        row = ArtifactListingService().select_completed_artifact_row(
            raw, artifact_id, "Report", "report", type_code=ArtifactTypeCode.REPORT
        )
        return NLMArtifactDownloadUrlResponse(
            url=None, format="markdown", content=row.report_markdown
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/notebooks/{notebook_id}/artifacts/{artifact_id}/download/mind-map",
    summary="Download mind map as JSON",
)
async def download_mind_map(notebook_id: str, artifact_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)
    try:
        note_service = NoteService(client._rpc_executor)
        mind_map_service = NoteBackedMindMapService(note_service)
        mind_maps = await mind_map_service.list_mind_maps(notebook_id)

        for mm in mind_maps:
            if isinstance(mm, list) and len(mm) > 0 and str(mm[0]) == artifact_id:
                content = mind_map_service.extract_content(mm)
                if content:
                    try:
                        tree = json.loads(content)
                    except json.JSONDecodeError:
                        tree = content
                    return NLMArtifactDownloadUrlResponse(url=None, format="json", content=tree)

        raw = await _list_raw(client, notebook_id)
        for row_data in raw:
            if not isinstance(row_data, list):
                continue
            from notebooklm.types import Artifact
            art = Artifact.from_api_response(row_data)
            if art.id == artifact_id and art.is_interactive_mind_map:
                rpc_result = await client.rpc_call(
                    RPCMethod.GET_INTERACTIVE_HTML, [artifact_id]
                )
                tree_json = extract_interactive_tree_leaf(
                    rpc_result, source="artifacts.download_mind_map"
                )
                tree = _parse_tree(tree_json)
                return NLMArtifactDownloadUrlResponse(url=None, format="json", content=tree)

        return JSONResponse({"error": "Mind map not found"}, status_code=404)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/notebooks/{notebook_id}/artifacts/{artifact_id}/download/data-table",
    summary="Download data table as CSV",
)
async def download_data_table(notebook_id: str, artifact_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)
    try:
        raw = await _list_raw(client, notebook_id)
        row = ArtifactListingService().select_completed_artifact_row(
            raw, artifact_id, "Data table", "data_table", type_code=ArtifactTypeCode.DATA_TABLE
        )
        csv_content = _parse_data_table_csv(row.data_table_raw_payload)
        return NLMArtifactDownloadUrlResponse(
            url=None, format="csv", content=csv_content
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/notebooks/{notebook_id}/artifacts/{artifact_id}/download/quiz",
    summary="Download quiz as JSON",
)
async def download_quiz(notebook_id: str, artifact_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)
    try:
        artifacts = await client.artifacts.list(notebook_id, ArtifactType.QUIZ)
        completed = [a for a in artifacts if a.is_completed and a.id == artifact_id]
        if not completed:
            return JSONResponse({"error": "Completed quiz not found"}, status_code=404)
        art = completed[0]
        rpc_result = await client.rpc_call(RPCMethod.GET_INTERACTIVE_HTML, [art.id])
        html_content = safe_index(
            rpc_result, 0, 9, 0,
            method_id=RPCMethod.GET_INTERACTIVE_HTML.value,
            source="artifacts.download_quiz"
        )
        app_data = _extract_app_data(html_content) if html_content else None
        return NLMArtifactDownloadUrlResponse(url=None, format="json", content=app_data)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/notebooks/{notebook_id}/artifacts/{artifact_id}/download/flashcards",
    summary="Download flashcards as JSON",
)
async def download_flashcards(notebook_id: str, artifact_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)
    try:
        artifacts = await client.artifacts.list(notebook_id, ArtifactType.FLASHCARDS)
        completed = [a for a in artifacts if a.is_completed and a.id == artifact_id]
        if not completed:
            return JSONResponse({"error": "Completed flashcards not found"}, status_code=404)
        art = completed[0]
        rpc_result = await client.rpc_call(RPCMethod.GET_INTERACTIVE_HTML, [art.id])
        html_content = safe_index(
            rpc_result, 0, 9, 0,
            method_id=RPCMethod.GET_INTERACTIVE_HTML.value,
            source="artifacts.download_flashcards"
        )
        app_data = _extract_app_data(html_content) if html_content else None
        return NLMArtifactDownloadUrlResponse(url=None, format="json", content=app_data)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ─────────────────────────────────────────────
# Export
# ─────────────────────────────────────────────


@router.post(
    "/notebooks/{notebook_id}/artifacts/{artifact_id}/export/docs",
    summary="Export a report to Google Docs",
)
async def export_to_docs(notebook_id: str, artifact_id: str, body: NLMExportRequest, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        result = await client.artifacts.export_report(
            notebook_id, artifact_id, title=body.title
        )
        return {"status": "exported", "title": body.title}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/artifacts/{artifact_id}/export/sheets",
    summary="Export a data table to Google Sheets",
)
async def export_to_sheets(notebook_id: str, artifact_id: str, body: NLMExportRequest, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        result = await client.artifacts.export_data_table(
            notebook_id, artifact_id, title=body.title
        )
        return {"status": "exported", "title": body.title}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
