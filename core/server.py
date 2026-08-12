import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from core.routers.deepseek import router as deepseek_router
from core.routers.gemini import router as gemini_router
from core.routers.gemini.pool import gemini_pool
from core.routers.keys import router as keys_router
from core.routers.profiles import router as profiles_router
from core.load_balancer import load_balancer
from core.session import (
    session_store,
    session_manager,
    validate_api_key,
    get_api_key_hash,
    VirtualSessionMiddleware
)

load_dotenv(override=False)

BASE = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def _extract_provider(path: str) -> str:
    parts = [p for p in path.split('/') if p]
    if len(parts) >= 2 and parts[0] == 'v1':
        return parts[1]
    return 'unknown'


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await gemini_pool.close_all()


security_bearer = HTTPBearer(auto_error=False)

app = FastAPI(
    title="Unofficial API Gateway",
    version="0.1.0",
    description="OpenAI-compatible API Gateway for DeepSeek and Gemini with Multi-Profile Load Balancing.",
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


session_middleware = VirtualSessionMiddleware(
    store=session_store,
    manager=session_manager,
    validate_key_fn=validate_api_key,
    get_key_hash_fn=get_api_key_hash,
    extract_provider_fn=_extract_provider
)
app.add_middleware(BaseHTTPMiddleware, dispatch=session_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=".*",
)

app.include_router(deepseek_router, prefix="/v1/deepseek")
app.include_router(gemini_router, prefix="/v1/gemini")
app.include_router(keys_router, prefix="/v1/keys")
app.include_router(profiles_router, prefix="/v1/profiles")


@app.get("/health", summary="Health check", tags=["System"])
def health():
    ds_active = len(load_balancer.get_active_profiles("deepseek"))
    gem_active = len(load_balancer.get_active_profiles("gemini"))
    return {
        "status": "ok",
        "deepseek_active_profiles": ds_active,
        "gemini_active_profiles": gem_active,
    }


WEB_DIST = Path(BASE) / ".." / "web" / "dist"
if WEB_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(WEB_DIST / "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    @app.get("/ui", include_in_schema=False)
    def serve_ui():
        return FileResponse(str(WEB_DIST / "index.html"))
else:
    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("core.server:app", host="0.0.0.0", port=8088, reload=True)
