from .router import router
from .helpers import _build_model_list


@router.get("/models", summary="List available NotebookLM models")
async def list_models():
    return {"object": "list", "data": _build_model_list()}
