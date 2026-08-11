import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv(override=True)

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "..", "Gemini-API", "src"))

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
    from core.routers.deepseek import router as deepseek_router
except ImportError:
    deepseek_router = None

try:
    from core.routers.gemini import router as gemini_router
except ImportError:
    gemini_router = None

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

    yield

    if gemini_client:
        await gemini_client.close()


security_bearer = HTTPBearer(auto_error=False)

app = FastAPI(
    title="Unofficial API Gateway",
    version="0.1.0",
    description="OpenAI-compatible API Gateway for DeepSeek and Gemini.",
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
app.include_router(keys_router, prefix="/v1/keys")


@app.get("/health", summary="Health check", tags=["System"])
def health():
    gemini_ok = getattr(app.state, "gemini_client", None) is not None
    return {
        "status": "ok",
        "gemini_connected": gemini_ok,
    }


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("core.server:app", host="0.0.0.0", port=8088, reload=True)
