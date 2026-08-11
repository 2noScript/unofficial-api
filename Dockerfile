FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY deepseek-api/ deepseek-api/
COPY Gemini-API/ Gemini-API/
RUN uv sync --frozen --no-dev

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY core/ core/
COPY deepseek-api/ deepseek-api/
COPY Gemini-API/ Gemini-API/
COPY web/dist/ web/dist/

# Persistent data directory for profiles, API keys, and session storage
RUN mkdir -p /data
ENV UNOFFICIAL_API_DATA_DIR=/data

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8088

CMD ["uvicorn", "core.server:app", "--host", "0.0.0.0", "--port", "8088"]
