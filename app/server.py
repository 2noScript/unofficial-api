import os
import sys
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Gemini-API/src"))

from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse
from gemini_webapi import GeminiClient

from app.routers.deepseek import router as deepseek_router
from app.routers.gemini import router as gemini_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    secure_1psid = os.environ.get("GEMINI_SECURE_1PSID")
    secure_1psidts = os.environ.get("GEMINI_SECURE_1PSIDTS")
    client = None

    if secure_1psid:
        client = GeminiClient(
            secure_1psid=secure_1psid,
            secure_1psidts=secure_1psidts,
        )
        try:
            await client.init(timeout=30, auto_close=False)
        except Exception as e:
            print(f"[Gemini] Init failed: {e}", file=sys.stderr)
            client = None

    app.state.gemini_client = client
    yield
    if client:
        await client.close()


app = FastAPI(
    title="Unofficial API Gateway",
    version="0.1.0",
    description=(
        "OpenAI-compatible API for DeepSeek and Gemini models.\n\n"
        "- **DeepSeek**: `deepseek-v3`, `deepseek-r1`, `deepseek-v4`, `deepseek-r4`\n"
        "- **Gemini**: `gemini-3-flash`, `gemini-3-pro`, `gemini-3-flash-thinking`, and more\n\n"
        "### Authentication\n"
        "Set environment variables in `.env` file before making requests."
    ),
    lifespan=lifespan,
)

app.include_router(deepseek_router, prefix="/v1/deepseek")
app.include_router(gemini_router, prefix="/v1/gemini")


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
    uvicorn.run("app.server:app", host="0.0.0.0", port=8000, reload=True)
