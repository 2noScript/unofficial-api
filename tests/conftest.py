import os
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import MagicMock, AsyncMock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "grok2api"))
sys.path.insert(0, os.path.join(BASE, "deepseek-api"))
sys.path.insert(0, os.path.join(BASE, "Gemini-API/src"))
sys.path.insert(0, os.path.join(BASE, "metaai-api", "src"))

from core.routers.deepseek import router as ds_router
from core.routers.gemini import router as gm_router
from core.routers.grok import router as gk_router
from core.routers.metaai import router as ma_router
from core.routers.notebooklm import router as nl_router
from core.routers.keys import router as keys_router


@asynccontextmanager
async def noop_lifespan(app: FastAPI):
    app.state.gemini_client = MagicMock()
    app.state.notebooklm_client = AsyncMock()
    app.state.metaai_client = MagicMock()
    app.state.grok_client = MagicMock()
    yield


@pytest.fixture(scope="session")
def app():
    app = FastAPI(lifespan=noop_lifespan)

    @app.middleware("http")
    async def fake_session_middleware(request: Request, call_next):
        request.state.session_data = {}
        request.state.virtual_session_id = "test-vid"
        return await call_next(request)

    app.include_router(ds_router, prefix="/v1/deepseek")
    app.include_router(gm_router, prefix="/v1/gemini")
    app.include_router(gk_router, prefix="/v1/grok")
    app.include_router(ma_router, prefix="/v1/metaai")
    app.include_router(nl_router, prefix="/v1/notebooklm")
    app.include_router(keys_router, prefix="/v1/keys")

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "gemini_connected": True,
            "notebooklm_connected": True,
            "metaai_connected": True,
            "grok_connected": True,
        }

    @app.get("/")
    def root():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/docs")

    return app


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer ua-test-test-test"}


@pytest.fixture
def sample_messages():
    return [{"role": "user", "content": "Hello"}]


def make_stream_chunks(text: str, response_id: str = "chatcmpl-test") -> list:
    chunks = []
    for i, char in enumerate(text):
        delta = {"role": "assistant"} if i == 0 else {}
        delta["content"] = char
        import json
        chunk = {
            "id": response_id,
            "object": "chat.completion.chunk",
            "created": 1700000000,
            "model": "test-model",
            "choices": [{"index": 0, "delta": delta, "finish_reason": None}],
        }
        chunks.append(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n")
    final_delta = {"role": "assistant"}
    final_chunk = {
        "id": response_id,
        "object": "chat.completion.chunk",
        "created": 1700000000,
        "model": "test-model",
        "choices": [{"index": 0, "delta": final_delta, "finish_reason": "stop"}],
    }
    chunks.append(f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n")
    chunks.append("data: [DONE]\n\n")
    return chunks
