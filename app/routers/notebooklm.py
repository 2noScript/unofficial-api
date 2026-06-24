import os
import json
import time
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from notebooklm import NotebookLMClient
from notebooklm.types import Notebook

router = APIRouter(tags=["NotebookLM"])


def _build_model_list() -> list[dict]:
    return [
        {
            "id": "notebooklm-2-0",
            "object": "model",
            "created": 1704067200,
            "owned_by": "google",
            "description": "NotebookLM - Source-grounded Q&A with Google's Gemini models",
        },
    ]


async def _get_client(request: Request) -> NotebookLMClient | None:
    return getattr(request.app.state, "notebooklm_client", None)


async def _require_client(request: Request) -> NotebookLMClient:
    client = await _get_client(request)
    if not client:
        raise ValueError("NotebookLM client not initialized. Login via `notebooklm login` first.")
    return client


# ─────────────────────────────────────────────
#  Models
# ─────────────────────────────────────────────

@router.get("/models", summary="List available NotebookLM models")
async def list_models():
    return {"object": "list", "data": _build_model_list()}


# ─────────────────────────────────────────────
#  Chat Completions
# ─────────────────────────────────────────────

@router.post(
    "/chat/completions",
    summary="Ask a question against a NotebookLM notebook (source-grounded Q&A)",
)
async def chat_completions(request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    body = await request.json()
    messages = body.get("messages", [])
    stream = body.get("stream", False)
    notebook_id = body.get("notebook_id")
    source_ids = body.get("source_ids")

    if not notebook_id:
        notebook_id = os.environ.get("NOTEBOOKLM_DEFAULT_NOTEBOOK_ID")
    if not notebook_id:
        return JSONResponse(
            {"error": "notebook_id is required. Set NOTEBOOKLM_DEFAULT_NOTEBOOK_ID or pass notebook_id in request."},
            status_code=400,
        )

    question = messages[-1]["content"] if messages else ""
    if not question:
        return JSONResponse({"error": "No question provided"}, status_code=400)

    ask_kwargs = {"notebook_id": notebook_id, "question": question}
    if source_ids:
        ask_kwargs["source_ids"] = source_ids

    if stream:
        return StreamingResponse(
            _stream_chat(client, notebook_id, question, source_ids),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    try:
        result = await client.chat.ask(**ask_kwargs)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    answer = result.answer or ""
    conv_id = getattr(result, "conversation_id", None)

    return JSONResponse({
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "notebooklm-2-0",
        "notebook_id": notebook_id,
        "conversation_id": conv_id,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": answer},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": len(answer.split()) if answer else 0,
            "total_tokens": len(answer.split()) if answer else 0,
        },
    })


async def _stream_chat(
    client: NotebookLMClient, notebook_id: str, question: str, source_ids: list[str] | None
) -> AsyncGenerator[str, None]:
    try:
        result = await client.chat.ask(
            notebook_id=notebook_id, question=question, source_ids=source_ids
        )
        answer = result.answer or ""
        for line in answer.split("\n"):
            if line:
                chunk = json.dumps({"choices": [{"delta": {"content": line + "\n"}}]})
                yield f"data: {chunk}\n\n"
    except Exception as e:
        data = json.dumps({"error": str(e)})
        yield f"data: {data}\n\n"
    yield "data: [DONE]\n\n"


# ─────────────────────────────────────────────
#  Notebooks
# ─────────────────────────────────────────────

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


# ─────────────────────────────────────────────
#  Sources
# ─────────────────────────────────────────────

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
