from fastapi import Request
from fastapi.responses import JSONResponse
from notebooklm.types import MindMapKind

from app.schemas import (
    NLMMindMapGenerateRequest,
    NLMMindMapListResponse,
    NLMMindMapRenameRequest,
    NLMMindMapResponse,
    NLMMindMapTreeResponse,
)

from .router import router
from .helpers import _require_client


def _mind_map_to_dict(m):
    return {
        "id": m.id,
        "notebook_id": m.notebook_id,
        "title": m.title,
        "kind": m.kind.value if hasattr(m.kind, "value") else str(m.kind),
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "tree": m.tree,
    }


def _parse_kind(kind_str: str | None) -> MindMapKind | None:
    if kind_str is None:
        return None
    try:
        return MindMapKind(kind_str)
    except ValueError:
        return None


@router.get(
    "/notebooks/{notebook_id}/mind-maps",
    summary="List all mind maps in a notebook",
)
async def list_mind_maps(notebook_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        maps = await client.mind_maps.list(notebook_id)
        data = [_mind_map_to_dict(m) for m in maps]
        resp = NLMMindMapListResponse(data=data)
        return resp.model_dump()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/notebooks/{notebook_id}/mind-maps/{mind_map_id}",
    summary="Get a mind map by ID",
)
async def get_mind_map(notebook_id: str, mind_map_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        mm = await client.mind_maps.get(notebook_id, mind_map_id)
        if mm is None:
            return JSONResponse({"error": "Mind map not found"}, status_code=404)
        return _mind_map_to_dict(mm)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/mind-maps/generate",
    summary="Generate a mind map",
    status_code=201,
)
async def generate_mind_map(
    notebook_id: str,
    body: NLMMindMapGenerateRequest,
    request: Request,
):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    kind = _parse_kind(body.kind)
    if kind is None:
        return JSONResponse(
            {"error": f"Invalid kind: {body.kind}. Options: note_backed, interactive"},
            status_code=400,
        )

    try:
        result = await client.mind_maps.generate(
            notebook_id,
            source_ids=body.source_ids,
            kind=kind,
            language=body.language,
            instructions=body.instructions,
            wait=body.wait,
        )
        return _mind_map_to_dict(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.patch(
    "/notebooks/{notebook_id}/mind-maps/{mind_map_id}",
    summary="Rename a mind map",
)
async def rename_mind_map(
    notebook_id: str,
    mind_map_id: str,
    body: NLMMindMapRenameRequest,
    request: Request,
):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    kind = _parse_kind(body.kind)

    try:
        result = await client.mind_maps.rename(
            notebook_id,
            mind_map_id,
            body.title,
            kind=kind,
            return_object=True,
        )
        if result is None:
            return JSONResponse({"error": "Mind map not found"}, status_code=404)
        return _mind_map_to_dict(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete(
    "/notebooks/{notebook_id}/mind-maps/{mind_map_id}",
    summary="Delete a mind map",
)
async def delete_mind_map(notebook_id: str, mind_map_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        await client.mind_maps.delete(notebook_id, mind_map_id)
        return {"status": "deleted", "mind_map_id": mind_map_id}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/notebooks/{notebook_id}/mind-maps/{mind_map_id}/tree",
    summary="Get the node tree for a mind map",
)
async def get_mind_map_tree(
    notebook_id: str,
    mind_map_id: str,
    request: Request,
    kind: str | None = None,
):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    mind_map_kind = _parse_kind(kind)

    try:
        tree = await client.mind_maps.get_tree(
            notebook_id,
            mind_map_id,
            kind=mind_map_kind,
        )
        if tree is None:
            return JSONResponse({"error": "Mind map tree not available"}, status_code=404)
        resp = NLMMindMapTreeResponse(**tree)
        return resp.model_dump()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
