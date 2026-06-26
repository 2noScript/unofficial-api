import os
import sys
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "..", "Gemini-API/src"))
sys.path.insert(0, os.path.join(BASE, "..", "metaai-api", "src"))
sys.path.insert(0, os.path.join(BASE, "..", "grok2api"))

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from fastapi import FastAPI, Depends
from fastapi.security import APIKeyHeader, HTTPBearer
from fastapi.responses import JSONResponse, RedirectResponse
from gemini_webapi import GeminiClient

from notebooklm import NotebookLMClient

from metaai_api import MetaAI
from core.routers.grok.client import GrokClient

from core.routers.deepseek import router as deepseek_router
from core.routers.gemini import router as gemini_router
from core.routers.notebooklm import router as notebooklm_router
from core.routers.metaai import router as metaai_router
from core.routers.grok import router as grok_router
from core.routers.keys import router as keys_router

from starlette.middleware.base import BaseHTTPMiddleware
from core.session import (
    session_store,
    session_manager,
    validate_api_key,
    get_api_key_hash,
    VirtualSessionMiddleware
)
from core.utils import parse_cookie


def _extract_provider(path: str) -> str:
    parts = [p for p in path.split('/') if p]
    if len(parts) >= 2 and parts[0] == 'v1':
        return parts[1]
    return 'unknown'


def validate_env():
    errors = []

    if os.environ.get("DEEPSEEK_COOKIE") or os.environ.get("DEEPSEEK_AUTH_TOKEN"):
        dc = os.environ.get("DEEPSEEK_COOKIE") or ""
        if not parse_cookie(dc, "ds_session_id"):
            errors.append("DeepSeek: missing ds_session_id. Set DEEPSEEK_COOKIE=\"ds_session_id=...\"")
        if not os.environ.get("DEEPSEEK_AUTH_TOKEN"):
            errors.append("DeepSeek: missing auth token. Set DEEPSEEK_AUTH_TOKEN")

    if os.environ.get("GEMINI_COOKIE"):
        gc = os.environ.get("GEMINI_COOKIE") or ""
        if not parse_cookie(gc, "__Secure-1PSID"):
            errors.append("Gemini: missing __Secure-1PSID. Set GEMINI_COOKIE=\"__Secure-1PSID=...\"")
        # __Secure-1PSIDTS is optional

    if os.environ.get("META_AI_COOKIE"):
        mc = os.environ.get("META_AI_COOKIE") or ""
        for key in ["datr", "abra_sess", "ecto_1_sess"]:
            if not parse_cookie(mc, key):
                errors.append(f"Meta AI: missing {key}. Set META_AI_COOKIE=\"...; {key}=...\"")

    if os.environ.get("GROK_COOKIE") or os.environ.get("GROK_PROXY_USER_AGENT") or os.environ.get("GROK_PROXY_BROWSER"):
        if not os.environ.get("GROK_COOKIE"):
            errors.append("Grok: missing cookie string. Set GROK_COOKIE")

    if os.environ.get("NOTEBOOKLM_STORAGE_PATH") or os.environ.get("NOTEBOOKLM_DEFAULT_NOTEBOOK_ID"):
        sp = os.environ.get("NOTEBOOKLM_STORAGE_PATH")
        if sp and not os.path.exists(sp):
            errors.append(f"NotebookLM: storage path not found: {sp}")
        if sp and not os.environ.get("NOTEBOOKLM_DEFAULT_NOTEBOOK_ID"):
            errors.append("NotebookLM: missing default notebook ID. Set NOTEBOOKLM_DEFAULT_NOTEBOOK_ID")

    if errors:
        msg = "\n".join(
            ["", "=" * 60, "  ENVIRONMENT VARIABLE ERRORS", "=" * 60]
            + [f"  \u2022 {e}" for e in errors]
            + ["=" * 60]
        )
        print(msg, file=sys.stderr)
        sys.exit(1)


validate_env()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Gemini
    gemini_cookie = os.environ.get("GEMINI_COOKIE") or ""
    secure_1psid = parse_cookie(gemini_cookie, "__Secure-1PSID")
    secure_1psidts = parse_cookie(gemini_cookie, "__Secure-1PSIDTS")
    gemini_client = None
    if secure_1psid:
        gemini_client = GeminiClient(
            secure_1psid=secure_1psid, secure_1psidts=secure_1psidts,)
        try:
            await gemini_client.init(timeout=30, auto_close=False)
        except Exception as e:
            print(f"[Gemini] Init failed: {e}", file=sys.stderr)
            gemini_client = None

    app.state.gemini_client = gemini_client

    # NotebookLM
    notebooklm_ctx = None
    notebooklm_client = None
    storage_path = os.environ.get("NOTEBOOKLM_STORAGE_PATH")
    if storage_path and os.path.exists(storage_path):
        try:
            notebooklm_ctx = NotebookLMClient.from_storage(path=storage_path)
            notebooklm_client = await notebooklm_ctx.__aenter__()
        except Exception as e:
            print(f"[NotebookLM] Init failed: {e}", file=sys.stderr)
            notebooklm_ctx = notebooklm_client = None
    elif storage_path:
        print(f"[NotebookLM] Storage path not found: {storage_path}", file=sys.stderr)

    app.state.notebooklm_client = notebooklm_client

    # Meta AI
    meta_cookie = os.environ.get("META_AI_COOKIE") or ""
    metaai_client = None
    cookies = {}
    for key in ["datr", "abra_sess", "ecto_1_sess"]:
        val = parse_cookie(meta_cookie, key)
        if val:
            cookies[key] = val
    if cookies:
        try:
            metaai_client = MetaAI(cookies=cookies)
        except Exception as e:
            print(f"[MetaAI] Init failed: {e}", file=sys.stderr)
            metaai_client = None

    app.state.metaai_client = metaai_client

    # Grok
    grok_client = None
    grok_cookies_str = os.environ.get("GROK_COOKIE")
    if grok_cookies_str:
        try:
            grok_client = GrokClient(
                cookies_str=grok_cookies_str,
                user_agent=os.environ.get("GROK_PROXY_USER_AGENT", ""),
                browser=os.environ.get("GROK_PROXY_BROWSER", ""),
            )
        except Exception as e:
            print(f"[Grok] Init failed: {e}", file=sys.stderr)
            grok_client = None

    app.state.grok_client = grok_client
    yield

    if gemini_client:
        await gemini_client.close()
    if notebooklm_ctx:
        await notebooklm_ctx.__aexit__(None, None, None)


security_bearer = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-Api-Key", auto_error=False)

app = FastAPI(
    title="Unofficial API Gateway",
    version="0.1.0",
    description=(
        "OpenAI-compatible API for DeepSeek, Gemini, NotebookLM, Meta AI, and Grok.\n\n"
        "- **DeepSeek**: `deepseek-v3`, `deepseek-r1`, `deepseek-v4`, `deepseek-r4`\n"
        "- **Gemini**: `gemini-3-flash`, `gemini-3-pro`, `gemini-3-flash-thinking`, and more\n"
        "- **NotebookLM**: `notebooklm-2-0` (source-grounded Q&A)\n"
        "- **Meta AI**: `llama-4` (chat, image generation, video generation)\n"
        "- **Grok**: `grok-4.20-auto`, `grok-4.20-fast`, `grok-4.20-reasoning`, `grok-4.3-beta`, and more (15+ models)\n\n"
        "### Authentication\n"
        "Set environment variables in `.env` file before making requests."
    ),
    lifespan=lifespan,
    dependencies=[Depends(security_bearer), Depends(api_key_header)],
)

session_middleware = VirtualSessionMiddleware(
    store=session_store,
    manager=session_manager,
    validate_key_fn=validate_api_key,
    get_key_hash_fn=get_api_key_hash,
    extract_provider_fn=_extract_provider
)
app.add_middleware(BaseHTTPMiddleware, dispatch=session_middleware)

app.include_router(deepseek_router, prefix="/v1/deepseek")
app.include_router(gemini_router, prefix="/v1/gemini")
app.include_router(notebooklm_router, prefix="/v1/notebooklm")
app.include_router(metaai_router, prefix="/v1/metaai")
app.include_router(grok_router, prefix="/v1/grok")
app.include_router(keys_router, prefix="/v1/keys")


@app.get("/health", summary="Health check", tags=["System"])
def health():
    gemini_ok = getattr(app.state, "gemini_client", None) is not None
    notebooklm_ok = getattr(app.state, "notebooklm_client", None) is not None
    metaai_ok = getattr(app.state, "metaai_client", None) is not None
    grok_ok = getattr(app.state, "grok_client", None) is not None
    return {
        "status": "ok",
        "gemini_connected": gemini_ok,
        "notebooklm_connected": notebooklm_ok,
        "metaai_connected": metaai_ok,
        "grok_connected": grok_ok,
    }


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("core.server:app", host="0.0.0.0", port=8000, reload=True)
