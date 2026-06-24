from fastapi import Request
from fastapi.responses import JSONResponse

from .router import router
from .helpers import _require_client


@router.get("/notebooks/{notebook_id}/sources", summary="List sources in a notebook")
async def list_sources(notebook_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        sources = await client.sources.list(notebook_id)
        return {
            "object": "list",
            "data": [
                {
                    "id": s.id,
                    "display_name": s.display_name,
                    "source_type": getattr(s, "source_type", None),
                    "url": getattr(s, "url", None),
                }
                for s in sources
            ],
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/notebooks/{notebook_id}/sources", summary="Add a source to a notebook", status_code=201)
async def add_source(notebook_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    body = await request.json()
    source_type = body.get("type", "url")
    value = body.get("value", "")

    if not value:
        return JSONResponse({"error": "Source value is required"}, status_code=400)

    try:
        if source_type == "url":
            result = await client.sources.add_url(notebook_id, value)
        elif source_type == "text":
            result = await client.sources.add_text(notebook_id, value)
        else:
            return JSONResponse(
                {"error": f"Unsupported source type: {source_type}. Use 'url' or 'text'."},
                status_code=400,
            )

        return {"status": "added", "source_id": getattr(result, "id", None), "type": source_type}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete(
    "/notebooks/{notebook_id}/sources/{source_id}",
    summary="Delete a source from a notebook",
)
async def delete_source(notebook_id: str, source_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        await client.sources.delete(notebook_id, source_id)
        return {"status": "deleted", "source_id": source_id}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
