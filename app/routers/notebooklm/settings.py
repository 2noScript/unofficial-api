from fastapi import Request
from fastapi.responses import JSONResponse

from app.schemas import NLMSetLanguageRequest, NLMAccountLimitsResponse, NLMAccountTierResponse

from .router import router
from .helpers import _require_client


@router.get(
    "/settings/output-language",
    summary="Get the current output language setting",
)
async def get_output_language(request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        language = await client.settings.get_output_language()
        return {"language": language}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/settings/output-language",
    summary="Set the output language for artifact generation",
)
async def set_output_language(body: NLMSetLanguageRequest, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        result = await client.settings.set_output_language(body.language)
        return {"language": result}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/settings/account-limits",
    summary="Get account-level limits",
)
async def get_account_limits(request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        limits = await client.settings.get_account_limits()
        resp = NLMAccountLimitsResponse(
            notebook_limit=limits.notebook_limit,
            source_limit=limits.source_limit,
        )
        return resp.model_dump()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/settings/account-tier",
    summary="Get the account subscription tier",
)
async def get_account_tier(request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        tier = await client.settings.get_account_tier()
        resp = NLMAccountTierResponse(
            tier=tier.tier,
            plan_name=tier.plan_name,
        )
        return resp.model_dump()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
