import os
import json
import time
from typing import AsyncGenerator

from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse
from notebooklm import NotebookLMClient

from .router import router
from .helpers import _require_client


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
