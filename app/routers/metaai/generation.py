import time
import asyncio

from fastapi import Request
from fastapi.responses import JSONResponse
from metaai_api import MetaAI

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
            {"error": "MetaAI client not initialized. Set META_AI_DATR in .env."},
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
            {"error": "MetaAI client not initialized. Set META_AI_DATR in .env."},
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
