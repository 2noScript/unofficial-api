# Unofficial API Gateway

> **⚠️ Unofficial & Experimental**
>
> This project uses **undocumented, unofficial APIs** from DeepSeek, Google (Gemini), Google (NotebookLM), Meta (Meta AI), and xAI (Grok). These are **not officially supported** by any provider.
>
> - APIs can break or change without notice
> - Rate limits and throttling apply
> - Credentials (cookies) expire and must be refreshed
> - **Not affiliated** with DeepSeek or Google
> - For **prototypes, research, and personal projects** only

OpenAI-compatible REST API for **DeepSeek**, **Gemini**, **NotebookLM**, **Meta AI**, and **Grok**.

> 📖 [Architecture Overview](docs/ARCHITECTURE.md) — project structure, lifecycle, client types, streaming, auth, Docker
>
> 🔄 [Provider Conversion Details](docs/CONVERSION.md) — OpenAI field mapping per provider
>
> 🔑 [Authentication & Session Management](docs/auth.md) — API key management, Swagger UI setup, conversation context isolation

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
5. Generate an API key (required for all chat requests):
   ```bash
   curl -X POST http://localhost:8000/v1/keys/generate \
     -H "Content-Type: application/json" \
     -d '{"name": "my-key"}'
   ```
   Save the returned `api_key` — pass it as `Authorization: Bearer <key>` on every request.

| Provider | Credentials Guide | Specific Endpoints |
|---|---|---|
| DeepSeek | [`docs/deepseek.md`](docs/deepseek.md) | [expert models, reasoning_content](docs/deepseek.md#chat-completions--additional-fields) |
| Gemini | [`docs/gemini.md`](docs/gemini.md) | [Chats, Gems, Deep Research](docs/gemini.md#provider-specific-endpoints) |
| NotebookLM | [`docs/notebooklm.md`](docs/notebooklm.md) | [Notebooks, Sources, Notes, Chat, Research, Sharing, Settings, Mind Maps](docs/notebooklm.md) · [Artifacts (~32)](docs/notebooklm-artifacts.md) |
| Meta AI | [`docs/metaai.md`](docs/metaai.md) | [Image Gen, Video Gen, Image Upload, Video Extend, Media](docs/metaai.md#provider-specific-endpoints) |
| Grok | [`docs/grok.md`](docs/grok.md) | None |

## Configuration

```bash
cp .env.example .env
```

| Env var | Required | Description |
|---|---|---|
| `DEEPSEEK_COOKIE` | ✅ | DeepSeek full cookie string — [docs](docs/deepseek.md) |
| `DEEPSEEK_AUTH_TOKEN` | ✅ | DeepSeek `authorization` header — [docs](docs/deepseek.md) |
| `GEMINI_COOKIE` | ✅ | Gemini full cookie string — [docs](docs/gemini.md) |
| `NOTEBOOKLM_STORAGE_PATH` | ❌* | Path to `storage_state.json` — [docs](docs/notebooklm.md) |
| `NOTEBOOKLM_DEFAULT_NOTEBOOK_ID` | ❌* | Notebook ID for chat completions — [docs](docs/notebooklm.md) |
| `META_AI_COOKIE` | ✅ | Meta AI full cookie string — [docs](docs/metaai.md) |
| `GROK_COOKIE`, `GROK_PROXY_USER_AGENT`, `GROK_PROXY_BROWSER` | ✅ | Grok cookies + config — [docs](docs/grok.md) |
| `SESSION_TTL_DAYS` | ❌ | Session lifetime in days after last use. `0` = never expire. Default: `7` |
| `SESSION_MAX_SESSIONS` | ❌ | Max sessions kept in memory. Default: `5000` |
| `API_KEY_SECRET` | ❌ | HMAC secret for API key signing. Change in production. |
| `UNOFFICIAL_API_DATA_DIR` | ❌ | Directory for `api_keys.json`, `sessions.json`, `machine_id`. Default: `~/.unofficial-api` |


\*Required for NotebookLM endpoints. `NOTEBOOKLM_DEFAULT_NOTEBOOK_ID` required for chat completions.

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

| Endpoint | Method | DeepSeek | Gemini | NotebookLM | Meta AI | Grok |
|---|---|---|---|---|---|---|
| `GET /v1/{provider}/models` | GET | ✅ | ✅ | ✅ | ✅ | ✅ |
| `POST /v1/{provider}/chat/completions` | POST | ✅ | ✅ | ✅ | ✅ | ✅ |

### Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `model` | string | ✅ | — | Model ID (e.g. `deepseek-v3`, `gemini-3-flash`, `notebooklm-2-0`, `llama-4`, `grok-4.20-auto`) |
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

## System

| Endpoint | Method | Description |
|---|---|---|
| `GET /health` | GET | Provider connection status |
| `GET /` | GET | Redirects to Swagger UI |

## API Key Management

| Endpoint | Method | Description |
|---|---|---|
| `POST /v1/keys/generate` | POST | Generate a new API key |
| `GET /v1/keys` | GET | List all API keys (masked) |
| `POST /v1/keys/revoke` | POST | Deactivate an API key |

Key management endpoints do **not** require authentication to allow bootstrapping. See [docs/auth.md](docs/auth.md) for full details.

## Examples

All providers share the same request format — only the endpoint and model differ.
Replace `YOUR_API_KEY` with a key from `POST /v1/keys/generate`.

```bash
# DeepSeek
curl -s http://localhost:8000/v1/deepseek/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "deepseek-v3", "messages": [{"role": "user", "content": "Hello!"}]}'

# Gemini
curl -s http://localhost:8000/v1/gemini/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "gemini-3-flash", "messages": [{"role": "user", "content": "Hello!"}]}'

# Grok
curl -s http://localhost:8000/v1/grok/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "grok-4.20-auto", "messages": [{"role": "user", "content": "Hello!"}]}'

# Meta AI
curl -s http://localhost:8000/v1/metaai/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "llama-4", "messages": [{"role": "user", "content": "Hello!"}]}'

# NotebookLM
curl -s http://localhost:8000/v1/notebooklm/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "notebooklm-2-0", "messages": [{"role": "user", "content": "Summarize the sources"}]}'

# Continue a conversation (pass X-Session-Id from a previous response)
curl -s http://localhost:8000/v1/gemini/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "X-Session-Id: <session-id-from-previous-response>" \
  -H "Content-Type: application/json" \
  -d '{"model": "gemini-3-flash", "messages": [{"role": "user", "content": "What did I just ask?"}]}'
```

> For provider-specific endpoints (gems, research, notebooks, sources, image/video gen), see the respective doc.
