from fastapi import Request
from core.schemas import ModelList

from .router import router
from .helpers import _get_client, _build_model_list


@router.get(
    "/models",
    summary="List available Gemini models",
    response_model=ModelList,
)
async def list_models(request: Request):
    client = _get_client(request)
    models = _build_model_list(client)
    return {"object": "list", "data": models}
