from fastapi import Request
from fastapi.responses import JSONResponse
from notebooklm.types import ResearchSource

from app.schemas import (
    NLMResearchImportRequest,
    NLMResearchImportResponse,
    NLMResearchSourceResponse,
    NLMResearchStartRequest,
    NLMResearchStartResponse,
    NLMResearchTaskResponse,
    NLMResearchWaitRequest,
)

from .router import router
from .helpers import _require_client


def _research_task_to_dict(task):
    sources = [
        NLMResearchSourceResponse(
            url=s.url,
            title=s.title,
            result_type=s.result_type if hasattr(s, "result_type") else 1,
            research_task_id=s.research_task_id if hasattr(s, "research_task_id") else None,
            report_markdown=s.report_markdown if hasattr(s, "report_markdown") else "",
        )
        for s in getattr(task, "sources", []) or []
    ]
    subtasks = []
    for sub in getattr(task, "tasks", []) or []:
        subtasks.append(_research_task_to_dict(sub))
    return NLMResearchTaskResponse(
        task_id=task.task_id,
        status=task.status.value if hasattr(task.status, "value") else str(task.status),
        query=getattr(task, "query", ""),
        sources=sources,
        summary=getattr(task, "summary", ""),
        report=getattr(task, "report", ""),
        subtasks=subtasks,
    ).model_dump()


@router.post(
    "/notebooks/{notebook_id}/research/start",
    summary="Start a research session",
    status_code=201,
)
async def start_research(
    notebook_id: str,
    body: NLMResearchStartRequest,
    request: Request,
):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        result = await client.research.start(
            notebook_id,
            body.query,
            source=body.source,
            mode=body.mode,
        )
        if result is None:
            return JSONResponse({"error": "No research task was created"}, status_code=500)
        resp = NLMResearchStartResponse(
            task_id=result.task_id,
            report_id=result.report_id,
            notebook_id=result.notebook_id,
            query=result.query,
            mode=result.mode,
        )
        return resp.model_dump()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/notebooks/{notebook_id}/research/tasks/{task_id}",
    summary="Poll research task status and results",
)
async def get_research_task(
    notebook_id: str,
    task_id: str,
    request: Request,
):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        result = await client.research.poll(notebook_id, task_id=task_id)
        return _research_task_to_dict(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/research/tasks/{task_id}/wait",
    summary="Wait for research to complete",
)
async def wait_research(
    notebook_id: str,
    task_id: str,
    body: NLMResearchWaitRequest,
    request: Request,
):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        result = await client.research.wait_for_completion(
            notebook_id,
            task_id=task_id,
            timeout=body.timeout,
            initial_interval=body.interval,
        )
        return _research_task_to_dict(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/research/tasks/{task_id}/import",
    summary="Import selected research sources into the notebook",
    status_code=201,
)
async def import_research_sources(
    notebook_id: str,
    task_id: str,
    body: NLMResearchImportRequest,
    request: Request,
):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        sources = [
            ResearchSource(url=s.url, title=s.title) for s in body.sources
        ]
        imported = await client.research.import_sources(
            notebook_id, task_id, sources
        )
        resp = NLMResearchImportResponse(imported=imported)
        return resp.model_dump()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/research/tasks/{task_id}/import-verified",
    summary="Import research sources with timeout-tolerant verification",
    status_code=201,
)
async def import_research_sources_verified(
    notebook_id: str,
    task_id: str,
    body: NLMResearchImportRequest,
    request: Request,
):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        sources = [
            ResearchSource(url=s.url, title=s.title) for s in body.sources
        ]
        imported = await client.research.import_sources_with_verification(
            notebook_id, task_id, sources
        )
        resp = NLMResearchImportResponse(imported=imported)
        return resp.model_dump()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
