import os
import json
import time
from typing import AsyncGenerator

from fastapi import Request, Body
from fastapi.responses import JSONResponse, StreamingResponse
from notebooklm import NotebookLMClient
from notebooklm.types import ChatGoal, ChatMode, ChatResponseLength

from app.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    NLMChatConfigureRequest,
    NLMChatHistoryResponse,
    NLMChatModeRequest,
    NLMChatReferenceResponse,
    NLMChatTurnResponse,
)

from .router import router
from .helpers import _require_client


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

    messages = body.messages
    stream = body.stream

    question = messages[-1].content if messages else ""
    if not question:
        return JSONResponse({"error": "No question provided"}, status_code=400)

    if stream:
        return StreamingResponse(
            _stream_chat(client, notebook_id, question),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    try:
        result = await client.chat.ask(notebook_id=notebook_id, question=question)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    answer = result.answer or ""
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


async def _stream_chat(
    client: NotebookLMClient, notebook_id: str, question: str
) -> AsyncGenerator[str, None]:
    try:
        result = await client.chat.ask(
            notebook_id=notebook_id, question=question
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


@router.get(
    "/chat/conversation-id",
    summary="Get the most recent conversation ID",
)
async def get_conversation_id(request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    notebook_id = _require_notebook_id()
    if not notebook_id:
        return JSONResponse({"error": "NOTEBOOKLM_DEFAULT_NOTEBOOK_ID is not set in .env."}, status_code=400)

    try:
        conv_id = await client.chat.get_conversation_id(notebook_id)
        return {"conversation_id": conv_id}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/chat/history",
    summary="Get Q&A history for the most recent conversation",
)
async def get_chat_history(
    request: Request,
    limit: int = 100,
    conversation_id: str | None = None,
):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    notebook_id = _require_notebook_id()
    if not notebook_id:
        return JSONResponse({"error": "NOTEBOOKLM_DEFAULT_NOTEBOOK_ID is not set in .env."}, status_code=400)

    try:
        kwargs = {"notebook_id": notebook_id, "limit": limit}
        if conversation_id is not None:
            kwargs["conversation_id"] = conversation_id
        history = await client.chat.get_history(**kwargs)
        turns = [
            NLMChatTurnResponse(query=q, answer=a, turn_number=i)
            for i, (q, a) in enumerate(history)
        ]
        if conversation_id is None:
            conversation_id = await client.chat.get_conversation_id(notebook_id)
        resp = NLMChatHistoryResponse(conversation_id=conversation_id or "", turns=turns)
        return resp.model_dump()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/chat/conversations/{conversation_id}/turns",
    summary="Get turns for a specific conversation",
)
async def get_conversation_turns(
    conversation_id: str,
    request: Request,
    limit: int = 2,
):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    notebook_id = _require_notebook_id()
    if not notebook_id:
        return JSONResponse({"error": "NOTEBOOKLM_DEFAULT_NOTEBOOK_ID is not set in .env."}, status_code=400)

    try:
        data = await client.chat.get_conversation_turns(
            notebook_id, conversation_id, limit=limit
        )
        return {"conversation_id": conversation_id, "turns": data}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete(
    "/chat/conversations/{conversation_id}",
    summary="Delete a conversation",
)
async def delete_conversation(
    conversation_id: str,
    request: Request,
):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    notebook_id = _require_notebook_id()
    if not notebook_id:
        return JSONResponse({"error": "NOTEBOOKLM_DEFAULT_NOTEBOOK_ID is not set in .env."}, status_code=400)

    try:
        success = await client.chat.delete_conversation(notebook_id, conversation_id)
        if not success:
            return JSONResponse({"error": "Conversation not found"}, status_code=404)
        return {"status": "deleted", "conversation_id": conversation_id}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/chat/configure",
    summary="Configure chat persona and response settings",
)
async def configure_chat(
    body: NLMChatConfigureRequest,
    request: Request,
):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    notebook_id = _require_notebook_id()
    if not notebook_id:
        return JSONResponse({"error": "NOTEBOOKLM_DEFAULT_NOTEBOOK_ID is not set in .env."}, status_code=400)

    try:
        goal = ChatGoal[body.goal.upper()] if body.goal else None
    except (KeyError, AttributeError):
        return JSONResponse(
            {"error": f"Invalid goal: {body.goal}. Options: default, custom, learning_guide"},
            status_code=400,
        )

    try:
        response_length = ChatResponseLength[body.response_length.upper()] if body.response_length else None
    except (KeyError, AttributeError):
        return JSONResponse(
            {"error": f"Invalid response_length: {body.response_length}. Options: default, longer, shorter"},
            status_code=400,
        )

    try:
        await client.chat.configure(
            notebook_id,
            goal=goal,
            response_length=response_length,
            custom_prompt=body.custom_prompt,
        )
        return {"status": "configured", "notebook_id": notebook_id}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/chat/mode",
    summary="Set chat mode using predefined configuration",
)
async def set_chat_mode(
    body: NLMChatModeRequest,
    request: Request,
):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    notebook_id = _require_notebook_id()
    if not notebook_id:
        return JSONResponse({"error": "NOTEBOOKLM_DEFAULT_NOTEBOOK_ID is not set in .env."}, status_code=400)

    try:
        mode = ChatMode(body.mode)
    except ValueError:
        return JSONResponse(
            {"error": f"Invalid mode: {body.mode}. Options: default, learning_guide, concise, detailed"},
            status_code=400,
        )

    try:
        await client.chat.set_mode(notebook_id, mode)
        return {"status": "mode_set", "mode": body.mode}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
