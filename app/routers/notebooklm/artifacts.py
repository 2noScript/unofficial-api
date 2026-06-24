from fastapi import Request
from fastapi.responses import JSONResponse

from notebooklm._artifact.listing import ArtifactListingService
from notebooklm.rpc.types import (
    AudioFormat,
    AudioLength,
    ArtifactTypeCode,
    VideoFormat,
    VideoStyle,
)

from app.schemas import (
    NLMArtifactDownloadUrlResponse,
    NLMAudioGenerateRequest,
    NLMGenerateRequest,
    NLMGenerationStatusResponse,
    NLMVideoGenerateRequest,
    NLMWaitRequest,
)

from .helpers import (
    _generation_status_to_response,
    _require_client,
)
from .router import router


async def _resolve_source_ids(client, notebook_id: str, source_ids: list[str] | None) -> list[str]:
    if source_ids is not None:
        return source_ids
    return await client.notebooks.get_source_ids(notebook_id)


async def _get_artifact_url_from_raw(client, notebook_id: str, artifact_id: str, type_code: ArtifactTypeCode) -> str | None:
    listing = ArtifactListingService()
    raw = await listing.list_raw(notebook_id, rpc=client._rpc_executor)
    row = listing.select_completed_artifact_row(
        raw, artifact_id, "Artifact", "artifact", type_code=type_code
    )
    return row.artifact_url(type_code.value, suppress_drift=True)


# ─────────────────────────────────────────────
# Generate
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


# ─────────────────────────────────────────────
# Status / Wait
# ─────────────────────────────────────────────


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


# ─────────────────────────────────────────────
# Download
# ─────────────────────────────────────────────


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
