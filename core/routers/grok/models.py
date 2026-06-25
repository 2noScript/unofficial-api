from .router import router
from .helpers import GROK_MODELS


@router.get("/models", summary="List available Grok models")
async def list_models():
    return {"object": "list", "data": GROK_MODELS}
