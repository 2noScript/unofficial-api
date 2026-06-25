FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY notebooklm-py/ notebooklm-py/
RUN uv sync --frozen --no-dev

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY core/ core/
COPY deepseek-api/ deepseek-api/
COPY Gemini-API/ Gemini-API/
COPY metaai-api/ metaai-api/
COPY grok2api/ grok2api/
COPY notebooklm-py/ notebooklm-py/

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "core.server:app", "--host", "0.0.0.0", "--port", "8000"]
