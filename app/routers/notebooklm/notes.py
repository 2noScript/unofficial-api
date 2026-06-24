from fastapi import Request
from fastapi.responses import JSONResponse

from app.schemas import NLMNoteCreateRequest, NLMNoteListResponse, NLMNoteResponse, NLMNoteUpdateRequest

from .router import router
from .helpers import _require_client


@router.get("/notebooks/{notebook_id}/notes", summary="List all notes in a notebook")
async def list_notes(notebook_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        notes = await client.notes.list(notebook_id)
        data = [
            NLMNoteResponse(
                id=n.id,
                notebook_id=n.notebook_id,
                title=n.title,
                content=n.content,
                created_at=str(n.created_at) if n.created_at else None,
            )
            for n in notes
        ]
        resp = NLMNoteListResponse(data=data)
        return resp.model_dump()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/notebooks/{notebook_id}/notes/{note_id}",
    summary="Get a specific note by ID",
)
async def get_note(notebook_id: str, note_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        note = await client.notes.get(notebook_id, note_id)
        if note is None:
            return JSONResponse({"error": "Note not found"}, status_code=404)
        resp = NLMNoteResponse(
            id=note.id,
            notebook_id=note.notebook_id,
            title=note.title,
            content=note.content,
            created_at=str(note.created_at) if note.created_at else None,
        )
        return resp.model_dump()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/notes",
    summary="Create a new note",
    status_code=201,
)
async def create_note(notebook_id: str, body: NLMNoteCreateRequest, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        note = await client.notes.create(notebook_id, title=body.title, content=body.content)
        resp = NLMNoteResponse(
            id=note.id,
            notebook_id=note.notebook_id,
            title=note.title,
            content=note.content,
            created_at=str(note.created_at) if note.created_at else None,
        )
        return resp.model_dump()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.patch(
    "/notebooks/{notebook_id}/notes/{note_id}",
    summary="Update a note",
)
async def update_note(notebook_id: str, note_id: str, body: NLMNoteUpdateRequest, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        await client.notes.update(notebook_id, note_id, content=body.content, title=body.title)
        return {"status": "updated", "note_id": note_id}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete(
    "/notebooks/{notebook_id}/notes/{note_id}",
    summary="Delete a note",
)
async def delete_note(notebook_id: str, note_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        await client.notes.delete(notebook_id, note_id)
        return {"status": "deleted", "note_id": note_id}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
