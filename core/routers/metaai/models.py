from .router import router
from .helpers import META_MODELS


@router.get("/models", summary="List available MetaAI models")
async def list_models():
    return {"object": "list", "data": META_MODELS}
