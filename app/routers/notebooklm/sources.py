import io
import os
import tempfile
from pathlib import Path

from fastapi import Request, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.schemas import (
    NLMSourceAddDriveRequest,
    NLMSourceAddTextRequest,
    NLMSourceAddUrlRequest,
    NLMSourceDetailResponse,
    NLMSourceFulltextResponse,
    NLMSourceGuideResponse,
    NLMSourceListResponse,
    NLMSourceRenameRequest,
    NLMSourceWaitRequest,
)

from .router import router
from .helpers import _require_client

_SOURCE_STATUS_STR = {1: "processing", 2: "ready", 3: "error", 5: "preparing"}


def _source_to_dict(s):
    status = int(s.status) if hasattr(s, "status") and s.status else 2
    return {
        "id": s.id,
        "title": s.title,
        "source_type": s.kind.value if hasattr(s, "kind") and s.kind else None,
        "url": s.url,
        "status": status,
        "status_str": _SOURCE_STATUS_STR.get(status, "unknown"),
        "created_at": str(s.created_at) if hasattr(s, "created_at") and s.created_at else None,
        "is_ready": s.is_ready if hasattr(s, "is_ready") else True,
        "is_processing": s.is_processing if hasattr(s, "is_processing") else False,
        "is_error": s.is_error if hasattr(s, "is_error") else False,
    }


@router.get("/notebooks/{notebook_id}/sources", summary="List sources in a notebook")
async def list_sources(notebook_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        sources = await client.sources.list(notebook_id)
        data = [_source_to_dict(s) for s in sources]
        resp = NLMSourceListResponse(data=data)
        return resp.model_dump()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/notebooks/{notebook_id}/sources/{source_id}",
    summary="Get a specific source by ID",
)
async def get_source(notebook_id: str, source_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        source = await client.sources.get(notebook_id, source_id)
        if source is None:
            return JSONResponse({"error": "Source not found"}, status_code=404)
        resp = NLMSourceDetailResponse(**_source_to_dict(source))
        return resp.model_dump()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/sources",
    summary="Add a source to a notebook (generic)",
    status_code=201,
)
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
        return {"status": "added", "source_id": result.id if result else None, "type": source_type}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/sources/url",
    summary="Add a URL source",
    status_code=201,
)
async def add_url_source(notebook_id: str, body: NLMSourceAddUrlRequest, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        kwargs = {}
        if body.wait:
            kwargs["wait"] = True
            kwargs["wait_timeout"] = 120.0
        result = await client.sources.add_url(notebook_id, body.url, **kwargs)
        return {
            "status": "added",
            "source_id": result.id if result else None,
            "source_type": "url",
            "title": result.title if result else None,
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/sources/text",
    summary="Add a text source",
    status_code=201,
)
async def add_text_source(notebook_id: str, body: NLMSourceAddTextRequest, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        result = await client.sources.add_text(
            notebook_id,
            body.title,
            body.content,
            wait=body.wait,
            wait_timeout=120.0,
            idempotent=body.idempotent,
        )
        return {
            "status": "added",
            "source_id": result.id if result else None,
            "source_type": "text",
            "title": result.title if result else None,
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/sources/file",
    summary="Add a file source (multipart upload)",
    status_code=201,
)
async def add_file_source(
    notebook_id: str,
    request: Request,
    file: UploadFile = File(..., description="File to upload"),
    title: str = Form("", description="Optional source title"),
    wait: bool = Form(False, description="Wait for processing to complete"),
):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    if not file.filename:
        return JSONResponse({"error": "No file provided"}, status_code=400)

    try:
        content = await file.read()
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            kwargs = {}
            if title:
                kwargs["title"] = title
            if wait:
                kwargs["wait"] = True
                kwargs["wait_timeout"] = 120.0
            result = await client.sources.add_file(notebook_id, tmp_path, **kwargs)
            return {
                "status": "added",
                "source_id": result.id if result else None,
                "source_type": "file",
                "filename": file.filename,
                "title": result.title if result else None,
            }
        finally:
            os.unlink(tmp_path)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/sources/drive",
    summary="Add a Google Drive source",
    status_code=201,
)
async def add_drive_source(notebook_id: str, body: NLMSourceAddDriveRequest, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        result = await client.sources.add_drive(
            notebook_id,
            body.file_id,
            body.title,
            mime_type=body.mime_type,
            wait=body.wait,
            wait_timeout=120.0,
        )
        return {
            "status": "added",
            "source_id": result.id if result else None,
            "source_type": "drive",
            "title": result.title if result else None,
        }
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


@router.patch(
    "/notebooks/{notebook_id}/sources/{source_id}",
    summary="Rename a source",
)
async def rename_source(notebook_id: str, source_id: str, body: NLMSourceRenameRequest, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        result = await client.sources.rename(notebook_id, source_id, body.title, return_object=True)
        if result is None:
            return JSONResponse({"error": "Source not found"}, status_code=404)
        resp = NLMSourceDetailResponse(**_source_to_dict(result))
        return resp.model_dump()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/sources/{source_id}/refresh",
    summary="Refresh a source to get updated content",
)
async def refresh_source(notebook_id: str, source_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        changed = await client.sources.refresh(notebook_id, source_id)
        return {"status": "refreshed" if changed else "up_to_date", "source_id": source_id}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/notebooks/{notebook_id}/sources/{source_id}/freshness",
    summary="Check if a source needs refreshing",
)
async def check_freshness(notebook_id: str, source_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        stale = await client.sources.check_freshness(notebook_id, source_id)
        return {"source_id": source_id, "needs_refresh": stale}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/notebooks/{notebook_id}/sources/{source_id}/guide",
    summary="Get AI-generated source guide (summary + keywords)",
)
async def get_source_guide(notebook_id: str, source_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        guide = await client.sources.get_guide(notebook_id, source_id)
        resp = NLMSourceGuideResponse(
            source_id=source_id,
            summary=guide.summary,
            keywords=list(guide.keywords),
        )
        return resp.model_dump()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/notebooks/{notebook_id}/sources/{source_id}/fulltext",
    summary="Get full text content of a source",
)
async def get_source_fulltext(
    notebook_id: str,
    source_id: str,
    request: Request,
    format: str = "text",
):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        fmt = "markdown" if format == "markdown" else "text"
        fulltext = await client.sources.get_fulltext(notebook_id, source_id, output_format=fmt)
        resp = NLMSourceFulltextResponse(
            source_id=fulltext.source_id,
            title=fulltext.title,
            content=fulltext.content,
            char_count=fulltext.char_count,
            url=fulltext.url,
            source_type=fulltext.kind.value if hasattr(fulltext, "kind") and fulltext.kind else None,
        )
        return resp.model_dump()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/sources/{source_id}/wait",
    summary="Wait for a source to become ready",
)
async def wait_source(
    notebook_id: str,
    source_id: str,
    body: NLMSourceWaitRequest,
    request: Request,
):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        result = await client.sources.wait_until_ready(
            notebook_id,
            source_id,
            timeout=body.timeout,
            initial_interval=body.initial_interval,
            max_interval=body.max_interval,
        )
        resp = NLMSourceDetailResponse(**_source_to_dict(result))
        return resp.model_dump()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
