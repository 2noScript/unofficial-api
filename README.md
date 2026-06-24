# Unofficial API Gateway

OpenAI-compatible REST API for **DeepSeek**, **Gemini**, and **NotebookLM**.

## Getting Started

1. Pick a provider → follow its credential guide
2. Copy and fill `.env`:
   ```bash
   cp .env.example .env
   ```
3. Run the server:
   ```bash
   ./run.sh                  # local
   # or
   docker compose up -d      # Docker
   ```
4. Open Swagger UI: http://localhost:8000/docs

| Provider | Credentials Guide | Specific Endpoints |
|---|---|---|
| DeepSeek | [`docs/deepseek.md`](docs/deepseek.md) | None |
| Gemini | [`docs/gemini.md`](docs/gemini.md) | [Chats, Gems, Deep Research](docs/gemini.md#provider-specific-endpoints) |
| NotebookLM | [`docs/notebooklm.md`](docs/notebooklm.md) | [Notebooks, Sources](docs/notebooklm.md#provider-specific-endpoints) |

## Configuration

```bash
cp .env.example .env
```

| Env var | Required | Description |
|---|---|---|
| `DEEPSEEK_SESSION_ID` | ✅ | DeepSeek `ds_session_id` cookie — [docs](docs/deepseek.md) |
| `DEEPSEEK_AUTH_TOKEN` | ✅ | DeepSeek `authorization` cookie — [docs](docs/deepseek.md) |
| `GEMINI_SECURE_1PSID` | ✅ | Google `__Secure-1PSID` cookie — [docs](docs/gemini.md) |
| `GEMINI_SECURE_1PSIDTS` | ❌ | Google `__Secure-1PSIDTS` cookie — [docs](docs/gemini.md) |
| `NOTEBOOKLM_STORAGE_PATH` | ❌* | Path to `storage_state.json` — [docs](docs/notebooklm.md) |
| `NOTEBOOKLM_DEFAULT_NOTEBOOK_ID` | ❌ | Default notebook for chat completions |

\*Required for NotebookLM endpoints.

## Run

### Docker

```bash
# Build multi-platform
docker buildx build --platform linux/amd64,linux/arm64 -t 2noscript/unofficial-api:latest --push .

# Run
docker compose up -d
docker compose logs -f
docker compose down
```

### Local

```bash
./run.sh
```

## Common (OpenAI-compatible) Endpoints

These share the same format across all providers.

| Endpoint | Method | DeepSeek | Gemini | NotebookLM |
|---|---|---|---|---|
| `GET /v1/{provider}/models` | GET | ✅ | ✅ | ✅ |
| `POST /v1/{provider}/chat/completions` | POST | ✅ | ✅ | ✅ |

### Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `model` | string | ✅ | — | Model ID (e.g. `deepseek-v3`, `gemini-3-flash`, `notebooklm-2-0`) |
| `messages` | array | ✅ | — | `[{"role": "user", "content": "..."}]` |
| `stream` | bool | ❌ | `false` | Enable SSE streaming |

### Response

```json
{
  "id": "chatcmpl-1719000000",
  "object": "chat.completion",
  "created": 1719000000,
  "model": "deepseek-v3",
  "choices": [
    {
      "index": 0,
      "message": { "role": "assistant", "content": "..." },
      "finish_reason": "stop"
    }
  ],
  "usage": { "prompt_tokens": 0, "completion_tokens": 42, "total_tokens": 42 }
}
```

Streaming SSE format:
```
data: {"choices": [{"delta": {"content": "..."}}]}
data: [DONE]
```

### Provider-specific request fields

| Provider | Field | Type | Description |
|---|---|---|---|
| Gemini | `files` | array | File paths to attach |
| NotebookLM | `notebook_id` | string | Target notebook |
| NotebookLM | `source_ids` | array | Filter to specific sources |

See each provider doc for details.

## System

| Endpoint | Method | Description |
|---|---|---|
| `GET /health` | GET | Provider connection status |
| `GET /` | GET | Redirects to Swagger UI |

## Examples

### Basic chat

```bash
curl -s http://localhost:8000/v1/deepseek/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "deepseek-v3", "messages": [{"role": "user", "content": "Hello!"}]}'
```

### Streaming

```bash
curl -s -N http://localhost:8000/v1/deepseek/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "deepseek-v3", "messages": [{"role": "user", "content": "Count to 5"}], "stream": true}'
```

> For provider-specific endpoints (gems, research, notebooks, sources), see the respective doc.
