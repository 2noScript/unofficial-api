from fastapi import Request
from fastapi.responses import JSONResponse

from .router import router
from .helpers import _require_client


@router.get("/notebooks", summary="List all NotebookLM notebooks")
async def list_notebooks(request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        notebooks = await client.notebooks.list()
        return {
            "object": "list",
            "data": [
                {
                    "id": nb.id,
                    "title": nb.title,
                    "url": getattr(nb, "url", None),
                    "created_at": getattr(nb, "created_at", None),
                }
                for nb in notebooks
            ],
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/notebooks", summary="Create a new NotebookLM notebook", status_code=201)
async def create_notebook(request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    body = await request.json()
    title = body.get("title", "Untitled")

    try:
        nb = await client.notebooks.create(title=title)
        return {"id": nb.id, "title": nb.title, "status": "created"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/notebooks/{notebook_id}", summary="Get a NotebookLM notebook")
async def get_notebook(notebook_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        nb = await client.notebooks.get(notebook_id)
        if not nb:
            return JSONResponse({"error": "Notebook not found"}, status_code=404)
        return {"id": nb.id, "title": nb.title, **({"url": nb.url} if hasattr(nb, "url") else {})}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/notebooks/{notebook_id}", summary="Delete a NotebookLM notebook")
async def delete_notebook(notebook_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        await client.notebooks.delete(notebook_id)
        return {"status": "deleted", "notebook_id": notebook_id}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
