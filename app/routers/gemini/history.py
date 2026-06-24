from fastapi import Request
from fastapi.responses import JSONResponse

from .router import router
from .helpers import _require_client
from app.schemas import ChatInfoSchema, ChatHistorySchema


@router.get(
    "/chats",
    summary="List recent Gemini chat conversations",
)
async def list_chats(request: Request):
    client = _require_client(request)
    if isinstance(client, JSONResponse):
        return client

    try:
        chats = client.list_chats()
        if not chats:
            return {"object": "list", "data": []}
        return {
            "object": "list",
            "data": [
                ChatInfoSchema(
                    cid=c.cid,
                    title=c.title or f"Chat({c.cid})",
                    is_pinned=c.is_pinned,
                    timestamp=c.timestamp,
                ).model_dump()
                for c in chats
            ],
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/chats/{cid}",
    summary="Read a Gemini chat conversation history",
    response_model=ChatHistorySchema,
)
async def read_chat(cid: str, request: Request):
    client = _require_client(request)
    if isinstance(client, JSONResponse):
        return client

    try:
        history = await client.read_chat(cid)
        if not history:
            return JSONResponse({"error": "Chat not found or still processing"}, status_code=404)

        return ChatHistorySchema(
            cid=history.cid,
            turns=[
                {"role": t.role, "text": t.text} for t in history.turns
            ],
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete(
    "/chats/{cid}",
    summary="Delete a Gemini chat conversation",
)
async def delete_chat(cid: str, request: Request):
    client = _require_client(request)
    if isinstance(client, JSONResponse):
        return client

    try:
        await client.delete_chat(cid)
        return {"status": "deleted", "cid": cid}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
