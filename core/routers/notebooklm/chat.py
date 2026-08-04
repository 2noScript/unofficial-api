import os
import json
import time
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

from fastapi import Request, Body
from fastapi.responses import JSONResponse, StreamingResponse
from notebooklm import NotebookLMClient

from core.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    NLMChatReferenceResponse,
)
from core.stream import make_stream_chunk, make_error_chunk, STREAM_END
from core.utils import extract_text

from .router import router
from .helpers import _require_client
from core.session.adapters import get_adapter
from core.session.history import sync_and_get_history, append_assistant_message


def _require_notebook_id() -> str | None:
    return os.environ.get("NOTEBOOKLM_DEFAULT_NOTEBOOK_ID") or None


@router.post(
    "/chat/completions",
    summary="Ask a question against a NotebookLM notebook (source-grounded Q&A)",
    response_model=ChatCompletionResponse,
    response_model_exclude_none=True,
)
async def chat_completions(
    request: Request,
    body: ChatCompletionRequest = Body(
        openapi_examples={
            "basic": {
                "summary": "Basic chat",
                "value": {
                    "model": "notebooklm-2-0",
                    "messages": [{"role": "user", "content": "Summarize the sources"}],
                    "stream": False,
                },
            }
        }
    ),
):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    notebook_id = _require_notebook_id()
    if not notebook_id:
        return JSONResponse(
            {"error": "NOTEBOOKLM_DEFAULT_NOTEBOOK_ID is not set in .env."},
            status_code=400,
        )

    VALID_NLM_MODELS = {"notebooklm-2-0"}
    model = body.model or "notebooklm-2-0"
    if model not in VALID_NLM_MODELS:
        return JSONResponse(
            {"error": f"Model '{model}' not supported. Supported: {sorted(VALID_NLM_MODELS)}"},
            status_code=400,
        )

    messages = body.messages
    stream = body.stream

    question = extract_text(messages[-1].content) if messages else ""
    if not question:
        return JSONResponse({"error": "No question provided"}, status_code=400)
    logger.info("Request /v1/notebooklm/chat/completions: %s", body.model_dump_json())

    # Session integration
    adapter = get_adapter("notebooklm")
    session_data = getattr(request.state, "session_data", {})

    # Sync local history with incoming messages
    body_messages = [m.model_dump() for m in messages]
    sync_and_get_history(body_messages, session_data)

    if stream:
        return StreamingResponse(
            _stream_chat(client, "notebooklm-2-0", notebook_id, question, session_data, adapter),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    # Non-streaming with retry-on-session-error
    for attempt in range(2):
        session_args = adapter.inject(session_data, {})
        try:
            result = await client.chat.ask(notebook_id=notebook_id, question=question, **session_args)
        except Exception as e:
            err_str = str(e)
            if attempt == 0 and session_data.get("notebooklm_conversation_id"):
                logger.warning("NotebookLM session error, resetting: %s", err_str)
                adapter.clear_provider_session(session_data)
                continue
            return JSONResponse({"error": err_str}, status_code=500)

        # Extract session data
        session_data.update(adapter.extract(result, session_data))

        answer = result.answer or ""
        append_assistant_message(session_data, answer)

        refs = getattr(result, "references", [])
        refs_data = [
            NLMChatReferenceResponse(
                source_id=r.source_id or "",
                citation_number=r.citation_number,
                cited_text=r.cited_text,
            )
            for r in refs
        ]

        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "notebooklm-2-0",
            "notebook_id": notebook_id,
            "conversation_id": getattr(result, "conversation_id", None),
            "turn_number": getattr(result, "turn_number", None),
            "is_follow_up": getattr(result, "is_follow_up", False),
            "references": refs_data,
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
        }

    return JSONResponse({"error": "Failed after retry"}, status_code=500)


async def _stream_chat(
    client: NotebookLMClient, model: str, notebook_id: str, question: str, session_data: dict, adapter
) -> AsyncGenerator[str, None]:
    response_id = f"chatcmpl-{int(time.time())}"

    for attempt in range(2):
        session_args = adapter.inject(session_data, {})
        try:
            result = await client.chat.ask(
                notebook_id=notebook_id, question=question, **session_args
            )
        except Exception as e:
            err_str = str(e)
            if attempt == 0 and session_data.get("notebooklm_conversation_id"):
                logger.warning("NotebookLM stream session error, resetting: %s", err_str)
                adapter.clear_provider_session(session_data)
                continue
            yield make_error_chunk(err_str)
            yield STREAM_END
            return

        # Extract session data
        session_data.update(adapter.extract(result, session_data))
        answer = result.answer or ""
        append_assistant_message(session_data, answer)

        first = True
        for line in answer.split("\n"):
            if line:
                yield make_stream_chunk(model, line + "\n", response_id, is_first=first)
                first = False
        if not first:
            yield make_stream_chunk(model, "", response_id, is_final=True)
        yield STREAM_END
        return

    yield make_error_chunk("NotebookLM session failed after retry")
    yield STREAM_END
