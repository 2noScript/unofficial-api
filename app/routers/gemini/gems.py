from fastapi import Request
from fastapi.responses import JSONResponse

from .router import router
from .helpers import _require_client
from app.schemas import GemSchema, GemCreateRequest, GemUpdateRequest


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
