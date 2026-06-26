import os
import tempfile
import time
import asyncio
from pathlib import Path

from fastapi import Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from metaai_api import MetaAI, GenerationAPI

from .router import router
from .helpers import get_client, _executor


@router.post(
    "/images/generations",
    summary="Generate an image using Meta AI",
)
async def generate_image(request: Request):
    client = get_client(request)
    if not client:
        return JSONResponse(
            {"error": "MetaAI client not initialized. Set META_AI_COOKIE in .env."},
            status_code=503,
        )

    body = await request.json()
    prompt = body.get("prompt", "")
    orientation = body.get("orientation", "VERTICAL")
    num_images = body.get("n", 1)

    if not prompt:
        return JSONResponse({"error": "prompt is required"}, status_code=400)

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor,
            lambda: client.generate_image_new(
                prompt=prompt,
                orientation=orientation.upper(),
                num_images=num_images,
            ),
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    return JSONResponse({
        "created": int(time.time()),
        "data": [
            {"url": url} for url in (result.get("image_urls") or [])
        ],
        "meta": {
            "success": result.get("success", False),
            "status": result.get("status"),
            "prompt": prompt,
            "orientation": orientation,
        },
    })


@router.post(
    "/videos/generations",
    summary="Generate a video using Meta AI",
)
async def generate_video(request: Request):
    client = get_client(request)
    if not client:
        return JSONResponse(
            {"error": "MetaAI client not initialized. Set META_AI_COOKIE in .env."},
            status_code=503,
        )

    body = await request.json()
    prompt = body.get("prompt", "")
    auto_poll = body.get("auto_poll", True)

    if not prompt:
        return JSONResponse({"error": "prompt is required"}, status_code=400)

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor,
            lambda: client.generate_video_new(
                prompt=prompt,
                auto_poll=auto_poll,
            ),
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    return JSONResponse({
        "created": int(time.time()),
        "data": [
            {"url": url} for url in (result.get("video_urls") or [])
        ],
        "meta": {
            "success": result.get("success", False),
            "status": result.get("status"),
            "processing": result.get("processing", False),
            "conversation_id": result.get("conversation_id"),
            "media_ids": result.get("media_ids", []),
            "prompt": prompt,
        },
    })


@router.post(
    "/images/upload",
    summary="Upload an image to Meta AI",
    status_code=201,
)
async def upload_image(
    request: Request,
    file: UploadFile = File(..., description="Image file to upload"),
):
    client = get_client(request)
    if not client:
        return JSONResponse(
            {"error": "MetaAI client not initialized. Set META_AI_COOKIE in .env."},
            status_code=503,
        )

    if not file.filename:
        return JSONResponse({"error": "No file provided"}, status_code=400)

    try:
        content = await file.read()
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                _executor,
                lambda: client.upload_image(tmp_path),
            )
        finally:
            os.unlink(tmp_path)

        return JSONResponse({
            "status": "uploaded",
            "filename": file.filename,
            "media_id": result.get("media_id") if isinstance(result, dict) else result,
            "result": result,
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


def _get_gen_api(client):
    cookies = client.get_cookies_dict() if hasattr(client, "get_cookies_dict") else {}
    return GenerationAPI(cookies=cookies)


@router.get(
    "/media/{media_id}",
    summary="Get media details by ID",
)
async def get_media(media_id: str, request: Request):
    client = get_client(request)
    if not client:
        return JSONResponse(
            {"error": "MetaAI client not initialized."}, status_code=503
        )

    try:
        loop = asyncio.get_event_loop()
        gen_api = _get_gen_api(client)
        result = await loop.run_in_executor(
            _executor, lambda: gen_api.fetch_media_by_id(media_id)
        )
        return {"media_id": media_id, "media": result}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/media/{media_id}/status",
    summary="Get media processing status",
)
async def get_media_status(media_id: str, request: Request):
    client = get_client(request)
    if not client:
        return JSONResponse(
            {"error": "MetaAI client not initialized."}, status_code=503
        )

    try:
        loop = asyncio.get_event_loop()
        gen_api = _get_gen_api(client)
        result = await loop.run_in_executor(
            _executor, lambda: gen_api.fetch_media_status(media_id)
        )
        return {"media_id": media_id, "status": result}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/videos/extend",
    summary="Extend an existing generated video",
    status_code=201,
)
async def extend_video(request: Request):
    client = get_client(request)
    if not client:
        return JSONResponse(
            {"error": "MetaAI client not initialized. Set META_AI_COOKIE in .env."},
            status_code=503,
        )

    body = await request.json()
    media_id = body.get("media_id", "")
    auto_poll = body.get("auto_poll", True)

    if not media_id:
        return JSONResponse({"error": "media_id is required"}, status_code=400)

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor,
            lambda: client.extend_video(
                media_id=media_id,
                auto_poll=auto_poll,
            ),
        )
        return JSONResponse({
            "status": "extended",
            "media_id": media_id,
            "result": result,
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
