import os
import sys
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "..", "deepseek-api"))
sys.path.insert(0, os.path.join(BASE, "..", "DeepSeek-API", "src"))
sys.path.insert(0, os.path.join(BASE, "..", "Gemini-API", "src"))
sys.path.insert(0, os.path.join(BASE, "..", "metaai-api", "src"))
sys.path.insert(0, os.path.join(BASE, "..", "grok2api"))

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse, RedirectResponse

try:
    from gemini_webapi import GeminiClient
except ImportError:
    GeminiClient = None

try:
    from notebooklm import NotebookLMClient
except ImportError:
    NotebookLMClient = None

try:
    from metaai_api import MetaAI
except ImportError:
    MetaAI = None

try:
    from core.routers.grok.client import GrokClient
except ImportError:
    GrokClient = None

try:
    from core.routers.deepseek import router as deepseek_router
except ImportError:
    deepseek_router = None

try:
    from core.routers.gemini import router as gemini_router
except ImportError:
    gemini_router = None

try:
    from core.routers.notebooklm import router as notebooklm_router
except ImportError:
    notebooklm_router = None

try:
    from core.routers.metaai import router as metaai_router
except ImportError:
    metaai_router = None

try:
    from core.routers.grok import router as grok_router
except ImportError:
    grok_router = None

from core.routers.keys import router as keys_router

from starlette.middleware.base import BaseHTTPMiddleware
from core.session import (
    session_store,
    session_manager,
    validate_api_key,
    get_api_key_hash,
    VirtualSessionMiddleware
)
from core.utils import parse_cookie, validate_env


def _extract_provider(path: str) -> str:
    parts = [p for p in path.split('/') if p]
    if len(parts) >= 2 and parts[0] == 'v1':
        return parts[1]
    return 'unknown'


validate_env()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Gemini
    gemini_cookie = os.environ.get("GEMINI_COOKIE") or ""
    secure_1psid = parse_cookie(gemini_cookie, "__Secure-1PSID")
    secure_1psidts = parse_cookie(gemini_cookie, "__Secure-1PSIDTS")
    gemini_client = None
    if GeminiClient and secure_1psid:
        gemini_client = GeminiClient(
            secure_1psid=secure_1psid, secure_1psidts=secure_1psidts,)
        try:
            await gemini_client.init(timeout=30, auto_close=False)
            from gemini_webapi.constants import AccountStatus
            if getattr(gemini_client, "account_status", None) == AccountStatus.UNAUTHENTICATED:
                print("[Gemini] Init warning: Account status is UNAUTHENTICATED (cookies invalid or expired). Disabling gemini_client.", file=sys.stderr)
                await gemini_client.close()
                gemini_client = None
        except Exception as e:
            print(f"[Gemini] Init failed: {e}", file=sys.stderr)
            gemini_client = None

    app.state.gemini_client = gemini_client

    # NotebookLM
    notebooklm_ctx = None
    notebooklm_client = None
    storage_path = os.environ.get("NOTEBOOKLM_STORAGE_PATH")
    if NotebookLMClient and storage_path and os.path.exists(storage_path):
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
    if MetaAI:
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
    if GrokClient and grok_cookies_str:
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

app = FastAPI(
    title="Unofficial API Gateway",
    version="0.1.0",
    description="OpenAI-compatible API Gateway for DeepSeek, Gemini, NotebookLM, Meta AI, and Grok.",
    dependencies=[Depends(security_bearer)],
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.getLogger("core.server").error("Unhandled exception for %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": f"Internal server error: {str(exc)}",
                "type": "api_error",
                "code": "internal_error"
            }
        }
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=".*",
)

session_middleware = VirtualSessionMiddleware(
    store=session_store,
    manager=session_manager,
    validate_key_fn=validate_api_key,
    get_key_hash_fn=get_api_key_hash,
    extract_provider_fn=_extract_provider
)
app.add_middleware(BaseHTTPMiddleware, dispatch=session_middleware)

if deepseek_router:
    app.include_router(deepseek_router, prefix="/v1/deepseek")
if gemini_router:
    app.include_router(gemini_router, prefix="/v1/gemini")
if notebooklm_router:
    app.include_router(notebooklm_router, prefix="/v1/notebooklm")
if metaai_router:
    app.include_router(metaai_router, prefix="/v1/metaai")
if grok_router:
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
    uvicorn.run("core.server:app", host="0.0.0.0", port=8088, reload=True)
