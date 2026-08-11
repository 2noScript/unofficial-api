import logging
from fastapi import Request, Body
from fastapi.responses import JSONResponse
from gemini_webapi import ChatSession
from gemini_webapi.constants import Model as GeminiModel

from .router import router
from .helpers import _resolve_model_name
from core.schemas import ChatCompletionRequest, ChatCompletionResponse
from core.session.adapters import get_adapter
from core.session.history import sync_and_get_history
from core.services.chat_service import chat_service
from core.services.gemini_strategy import GeminiStrategy

logger = logging.getLogger(__name__)
gemini_strategy = GeminiStrategy()


@router.post(
    "/chat/completions",
    summary="Create a chat completion using Gemini models",
    response_model=ChatCompletionResponse,
    response_model_exclude_none=True,
)
async def chat_completions(
    request: Request,
    body: ChatCompletionRequest = Body(
        openapi_examples={
            "basic": {
                "summary": "Basic chat",
                "value": {
                    "model": "gemini-3-flash",
                    "messages": [{"role": "user", "content": "Hello!"}],
                    "stream": False,
                },
            }
        }
    ),
):
    session_data = getattr(request.state, "session_data", {})
    VALID_GEMINI_MODELS = {m.model_name for m in GeminiModel if m is not GeminiModel.UNSPECIFIED}

    messages = [m.model_dump() for m in body.messages]
    stream = body.stream
    model = body.model or "gemini-3-flash"

    resolved_model = _resolve_model_name(model)
    if resolved_model not in VALID_GEMINI_MODELS:
        return JSONResponse(
            {"error": {"message": f"Model '{model}' not supported. Supported: {sorted(VALID_GEMINI_MODELS)}", "type": "invalid_request_error", "code": "model_not_found"}},
            status_code=400,
        )

    logger.info("Request /v1/gemini/chat/completions: %s", body.model_dump_json())

    adapter = get_adapter("gemini")
    sync_and_get_history(messages, session_data)

    if stream:
        return await chat_service.execute_stream(
            strategy=gemini_strategy,
            request=request,
            messages=messages,
            model=resolved_model,
            session_data=session_data,
            adapter=adapter,
        )

    return await chat_service.execute_chat(
        strategy=gemini_strategy,
        request=request,
        messages=messages,
        model=resolved_model,
        session_data=session_data,
        adapter=adapter,
    )
