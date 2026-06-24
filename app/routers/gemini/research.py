from fastapi import Request
from fastapi.responses import JSONResponse
from gemini_webapi import DeepResearchPlan

from .router import router
from .helpers import _require_client, _resolve_model_name
from app.schemas import (
    DeepResearchPlanRequest,
    DeepResearchPlanResponse,
    DeepResearchStartRequest,
    DeepResearchStatusSchema,
)


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

    plan = DeepResearchPlan(
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
