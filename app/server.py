import os
import sys
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Gemini-API/src"))

from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse
from gemini_webapi import GeminiClient

from notebooklm import NotebookLMClient

from app.routers.deepseek import router as deepseek_router
from app.routers.gemini import router as gemini_router
from app.routers.notebooklm import router as notebooklm_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Gemini
    secure_1psid = os.environ.get("GEMINI_SECURE_1PSID")
    secure_1psidts = os.environ.get("GEMINI_SECURE_1PSIDTS")
    gemini_client = None
    if secure_1psid:
        gemini_client = GeminiClient(
            secure_1psid=secure_1psid, secure_1psidts=secure_1psidts,
        )
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
    yield

    if gemini_client:
        await gemini_client.close()
    if notebooklm_ctx:
        await notebooklm_ctx.__aexit__(None, None, None)


app = FastAPI(
    title="Unofficial API Gateway",
    version="0.1.0",
    description=(
        "OpenAI-compatible API for DeepSeek, Gemini, and NotebookLM.\n\n"
        "- **DeepSeek**: `deepseek-v3`, `deepseek-r1`, `deepseek-v4`, `deepseek-r4`\n"
        "- **Gemini**: `gemini-3-flash`, `gemini-3-pro`, `gemini-3-flash-thinking`, and more\n"
        "- **NotebookLM**: `notebooklm-2-0` (source-grounded Q&A)\n\n"
        "### Authentication\n"
        "Set environment variables in `.env` file before making requests."
    ),
    lifespan=lifespan,
)

app.include_router(deepseek_router, prefix="/v1/deepseek")
app.include_router(gemini_router, prefix="/v1/gemini")
app.include_router(notebooklm_router, prefix="/v1/notebooklm")


@app.get("/health", summary="Health check", tags=["System"])
def health():
    gemini_ok = getattr(app.state, "gemini_client", None) is not None
    notebooklm_ok = getattr(app.state, "notebooklm_client", None) is not None
    return {
        "status": "ok",
        "gemini_connected": gemini_ok,
        "notebooklm_connected": notebooklm_ok,
    }


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.server:app", host="0.0.0.0", port=8000, reload=True)
