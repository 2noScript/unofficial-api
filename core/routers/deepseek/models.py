from deepseek_api import DEEPSEEK_MODELS
from .router import router


@router.get(
    "/models",
    summary="List available DeepSeek models",
)
async def list_models():
    return {"object": "list", "data": DEEPSEEK_MODELS}
