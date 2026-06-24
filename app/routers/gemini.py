import os
import sys
import json
import time
import asyncio
from typing import AsyncGenerator

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Gemini-API/src"))

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from gemini_webapi import GeminiClient
from gemini_webapi.constants import Model as GeminiModel
from app.schemas import (
    ChatCompletionRequest,
    ChatCompletionRequestGemini,
    ChatCompletionResponse,
    ChatInfoSchema,
    ChatHistorySchema,
    GemSchema,
    GemCreateRequest,
    GemUpdateRequest,
    DeepResearchPlanRequest,
    DeepResearchPlanResponse,
    DeepResearchStartRequest,
    DeepResearchStatusSchema,
    ModelList,
)

router = APIRouter(tags=["Gemini"])


def _get_client(request: Request) -> GeminiClient | None:
    return getattr(request.app.state, "gemini_client", None)


def _require_client(request: Request) -> GeminiClient | JSONResponse | None:
    client = _get_client(request)
    if not client:
        return JSONResponse(
            {"error": "Gemini client not initialized. Check credentials."},
            status_code=503,
        )
    return client


def _build_model_list(client: GeminiClient | None) -> list[dict]:
    known_names = set()
    models = []

    for member in GeminiModel:
        if member is GeminiModel.UNSPECIFIED:
            continue
        name = member.model_name
        if name not in known_names:
            known_names.add(name)
            display = name.replace("gemini-", "").replace("-", " ").title()
            models.append({
                "id": name,
                "object": "model",
                "created": 1704067200,
                "owned_by": "gemini",
                "description": f"Gemini {display}",
            })

    if client:
        avail = client.list_models()
        if avail:
            for m in avail:
                mid = m.model_name or m.model_id
                if mid and mid not in known_names:
                    known_names.add(mid)
                    models.append({
                        "id": mid,
                        "object": "model",
                        "created": 1704067200,
                        "owned_by": "gemini",
                        "description": m.description or f"Gemini {m.display_name}",
                    })

    return models


def _resolve_model_name(model: str) -> str:
    model_lower = model.lower()
    if model_lower.startswith("gemini-"):
        model_lower = model_lower[7:]
    for member in GeminiModel:
        if member is GeminiModel.UNSPECIFIED:
            continue
        if member.model_name == model or member.model_name == f"gemini-{model_lower}":
            return member.model_name
        if member.name.lower().replace("_", "-") == model_lower:
            return member.model_name
    return model


# ─────────────────────────────────────────────
#  Models
# ─────────────────────────────────────────────

@router.get(
    "/models",
    summary="List available Gemini models",
    response_model=ModelList,
)
async def list_models(request: Request):
    client = _get_client(request)
    models = _build_model_list(client)
    return {"object": "list", "data": models}


# ─────────────────────────────────────────────
#  Chat Completions
# ─────────────────────────────────────────────

@router.post(
    "/chat/completions",
    summary="Create a chat completion using Gemini models",
    response_model=ChatCompletionResponse,
)
async def chat_completions(request: Request, body: ChatCompletionRequestGemini):
    client = _require_client(request)
    if isinstance(client, JSONResponse):
        return client

    messages = [m.model_dump() for m in body.messages]
    stream = body.stream
    model = body.model or "gemini-3-flash"
    files = body.files

    resolved_model = _resolve_model_name(model)
    prompt = messages[-1]["content"] if messages else ""
    files_kw = {"files": files} if files else {}

    if stream:
        return StreamingResponse(
            _stream_gemini(client, prompt, resolved_model, files_kw),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    try:
        output = await client.generate_content(
            prompt=prompt, model=resolved_model, **files_kw
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    content = output.text or ""
    thoughts = output.thoughts or ""

    response_data = {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": resolved_model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": len(content.split()) if content else 0,
            "total_tokens": len(content.split()) if content else 0,
        },
    }

    if thoughts:
        response_data["choices"][0]["message"]["reasoning_content"] = thoughts

    return JSONResponse(response_data)


async def _stream_gemini(
    client: GeminiClient, prompt: str, resolved_model: str, files_kw: dict | None = None
) -> AsyncGenerator[str, None]:
    try:
        gen = client.generate_content_stream(prompt=prompt, model=resolved_model, **(files_kw or {}))
        async for chunk in gen:
            delta = chunk.text_delta
            if delta:
                data = json.dumps({"choices": [{"delta": {"content": delta}}]})
                yield f"data: {data}\n\n"
    except Exception as e:
        data = json.dumps({"error": str(e)})
        yield f"data: {data}\n\n"
    yield "data: [DONE]\n\n"


# ─────────────────────────────────────────────
#  Chat History
# ─────────────────────────────────────────────

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


# ─────────────────────────────────────────────
#  Gems (System Prompts)
# ─────────────────────────────────────────────

@router.get(
    "/gems",
    summary="List available Gemini Gems (system prompts)",
)
async def list_gems(request: Request):
    client = _require_client(request)
    if isinstance(client, JSONResponse):
        return client

    try:
        gems = await client.fetch_gems()
        return {
            "object": "list",
            "data": [
                GemSchema(
                    id=g.id,
                    name=g.name,
                    description=g.description,
                    prompt=g.prompt,
                    predefined=g.predefined,
                ).model_dump()
                for g in gems.values()
            ],
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/gems",
    summary="Create a custom Gemini Gem",
    status_code=201,
)
async def create_gem(body: GemCreateRequest, request: Request):
    client = _require_client(request)
    if isinstance(client, JSONResponse):
        return client

    try:
        gem = await client.create_gem(
            name=body.name,
            prompt=body.prompt,
            description=body.description,
        )
        return GemSchema(
            id=gem.id,
            name=gem.name,
            description=gem.description,
            prompt=gem.prompt,
            predefined=gem.predefined,
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.patch(
    "/gems/{gem_id}",
    summary="Update a custom Gemini Gem",
)
async def update_gem(gem_id: str, body: GemUpdateRequest, request: Request):
    client = _require_client(request)
    if isinstance(client, JSONResponse):
        return client

    try:
        gem = await client.update_gem(
            gem=gem_id,
            name=body.name,
            prompt=body.prompt,
            description=body.description,
        )
        return GemSchema(
            id=gem.id,
            name=gem.name,
            description=gem.description,
            prompt=gem.prompt,
            predefined=gem.predefined,
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete(
    "/gems/{gem_id}",
    summary="Delete a custom Gemini Gem",
)
async def delete_gem(gem_id: str, request: Request):
    client = _require_client(request)
    if isinstance(client, JSONResponse):
        return client

    try:
        await client.delete_gem(gem_id)
        return {"status": "deleted", "gem_id": gem_id}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ─────────────────────────────────────────────
#  Deep Research
# ─────────────────────────────────────────────

@router.post(
    "/research/plan",
    summary="Create a deep research plan",
    response_model=DeepResearchPlanResponse,
)
async def create_research_plan(body: DeepResearchPlanRequest, request: Request):
    client = _require_client(request)
    if isinstance(client, JSONResponse):
        return client

    resolved_model = _resolve_model_name(body.model) if body.model else None
    model_kw = {"model": resolved_model} if resolved_model else {}

    try:
        plan = await client.create_deep_research_plan(
            prompt=body.prompt, **model_kw
        )
        return DeepResearchPlanResponse(
            plan={
                "research_id": plan.research_id,
                "title": plan.title,
                "query": plan.query,
                "steps": plan.steps,
                "eta_text": plan.eta_text,
                "confirm_prompt": plan.confirm_prompt,
                "cid": plan.cid,
            },
            response_text=plan.response_text,
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/research/start",
    summary="Start a deep research plan",
)
async def start_research(body: DeepResearchStartRequest, request: Request):
    client = _require_client(request)
    if isinstance(client, JSONResponse):
        return client

    from gemini_webapi import DeepResearchPlan as DRPlan

    plan = DRPlan(
        research_id=body.plan.research_id,
        title=body.plan.title,
        query=body.plan.query,
        steps=body.plan.steps,
        eta_text=body.plan.eta_text,
        confirm_prompt=body.plan.confirm_prompt,
        cid=body.plan.cid,
    )

    try:
        output = await client.start_deep_research(
            plan=plan,
            confirm_prompt=body.confirm_prompt or plan.confirm_prompt,
        )
        return {
            "status": "started",
            "research_id": plan.research_id,
            "cid": plan.cid,
            "response": output.text if output else None,
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/research/{research_id}/status",
    summary="Get deep research status",
    response_model=DeepResearchStatusSchema,
)
async def get_research_status(research_id: str, request: Request):
    client = _require_client(request)
    if isinstance(client, JSONResponse):
        return client

    try:
        status = await client.get_deep_research_status(research_id)
        if not status:
            return JSONResponse({"error": "Research not found"}, status_code=404)

        return DeepResearchStatusSchema(
            research_id=status.research_id,
            state=status.state,
            title=status.title,
            query=status.query,
            cid=status.cid,
            notes=status.notes,
            done=status.done,
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
