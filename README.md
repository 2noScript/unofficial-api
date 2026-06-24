# Unofficial API Gateway

OpenAI-compatible REST API for **DeepSeek**, **Gemini**, and **NotebookLM**.

## Getting Credentials

### DeepSeek

1. Go to https://chat.deepseek.com and sign in
2. Open DevTools (F12) → **Application** → **Cookies** → `https://chat.deepseek.com`
3. Copy the cookie values:

| Cookie name | Env var | Required |
|---|---|---|
| `ds_session_id` | `DEEPSEEK_SESSION_ID` | ✅ |
| `authorization` | `DEEPSEEK_AUTH_TOKEN` | ✅ |

### Gemini

1. Go to https://gemini.google.com and sign in
2. Open DevTools (F12) → **Application** → **Cookies** → `https://gemini.google.com`
3. Copy the cookie values:

| Cookie name | Env var | Required |
|---|---|---|
| `__Secure-1PSID` | `GEMINI_SECURE_1PSID` | ✅ |
| `__Secure-1PSIDTS` | `GEMINI_SECURE_1PSIDTS` | ❌ (account-dependent) |

> Cookies expire. Re-extract them when requests start failing.

### NotebookLM

1. Install the CLI and log in (this will open a browser for Google sign-in):

```bash
pip install notebooklm-py
notebooklm login
```

2. The login creates a `storage_state.json` file (default: `~/.notebooklm/profiles/default/storage_state.json`).
3. Set `NOTEBOOKLM_STORAGE_PATH` to point to this file in your `.env`.

## Configuration

Copy the example file and fill in your credentials:

```bash
cp .env.example .env
```

| Env var | Required | Description |
|---|---|---|
| `DEEPSEEK_SESSION_ID` | ✅ | DeepSeek `ds_session_id` cookie value |
| `DEEPSEEK_AUTH_TOKEN` | ✅ | DeepSeek `authorization` cookie value |
| `GEMINI_SECURE_1PSID` | ✅ | Google `__Secure-1PSID` cookie value |
| `GEMINI_SECURE_1PSIDTS` | ❌ | Google `__Secure-1PSIDTS` cookie value |
| `NOTEBOOKLM_STORAGE_PATH` | ❌* | Path to `storage_state.json` from `notebooklm login` |
| `NOTEBOOKLM_DEFAULT_NOTEBOOK_ID` | ❌ | Default notebook ID for chat completions |

\*Required for NotebookLM endpoints.

## Run

### Docker

```bash
# Build & push multi-platform
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t 2noscript/unofficial-api:latest \
  --push .

# Run with compose
docker compose up -d
docker compose logs -f
docker compose down
```

### Local

```bash
./run.sh
```

Open Swagger UI: http://localhost:8000/docs

## API Reference

### Common (OpenAI-compatible)

These endpoints share the same request/response format across providers.

| Endpoint | Method | Description |
|---|---|---|
| `GET /v1/{provider}/models` | GET | List available models |
| `POST /v1/{provider}/chat/completions` | POST | Chat completion (stream + non-stream) |

**Supported providers:** `deepseek`, `gemini`, `notebooklm`

#### POST `/v1/{provider}/chat/completions` — Request body

| Field | Type | Required | Description |
|---|---|---|---|
| `model` | string | ✅ | Model ID (e.g. `deepseek-v3`, `gemini-3-flash`, `notebooklm-2-0`) |
| `messages` | array | ✅ | Array of `{role, content}` objects |
| `stream` | bool | ❌ | Enable SSE streaming (default: `false`) |
| `files` | array | ❌ | *(Gemini only)* File paths to attach |
| `notebook_id` | string | ❌* | *(NotebookLM only)* Target notebook |
| `source_ids` | array | ❌ | *(NotebookLM only)* Filter to specific source IDs |

\*Required for NotebookLM unless `NOTEBOOKLM_DEFAULT_NOTEBOOK_ID` is set.

#### POST `/v1/{provider}/chat/completions` — Response

Returns standard OpenAI chat completion format (`choices[].message.content`).

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

For streaming, each chunk follows the SSE format:

```
data: {"choices": [{"delta": {"content": "..."}}]}
data: [DONE]
```

> **Gemini note**: Supports `reasoning_content` in `choices[].message` for thinking models.
> **DeepSeek note**: V4/R4 expert mode is unsupported; falls back to default mode automatically.

---

### DeepSeek

No provider-specific endpoints beyond the common ones.

| Model IDs |
|---|
| `deepseek-v3` |
| `deepseek-r1` |
| `deepseek-v4` |
| `deepseek-r4` |

---

### Gemini

| Endpoint | Method | Description |
|---|---|---|
| `GET /v1/gemini/chats` | GET | List chat sessions |
| `GET /v1/gemini/chats/{cid}` | GET | Get chat history |
| `DELETE /v1/gemini/chats/{cid}` | DELETE | Delete chat session |
| `GET /v1/gemini/gems` | GET | List gems |
| `POST /v1/gemini/gems` | POST | Create a gem |
| `PATCH /v1/gemini/gems/{gem_id}` | PATCH | Update a gem |
| `DELETE /v1/gemini/gems/{gem_id}` | DELETE | Delete a gem |
| `POST /v1/gemini/research/plan` | POST | Create a deep research plan |
| `POST /v1/gemini/research/start` | POST | Start a deep research |
| `GET /v1/gemini/research/{id}/status` | GET | Get research status |

#### POST `/v1/gemini/gems` — Request body

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | ✅ | Gem name |
| `prompt` | string | ✅ | System prompt |
| `description` | string | ❌ | Optional description |

#### POST `/v1/gemini/research/plan` — Request body

| Field | Type | Required | Description |
|---|---|---|---|
| `prompt` | string | ✅ | Research topic or question |
| `model` | string | ❌ | Model override |

#### POST `/v1/gemini/research/start` — Request body

| Field | Type | Required | Description |
|---|---|---|---|
| `plan` | object | ✅ | Plan object from `/research/plan` response |
| `confirm_prompt` | string | ❌ | Override confirmation prompt |

#### GET `/v1/gemini/research/{id}/status` — Response

| Field | Type | Description |
|---|---|---|
| `research_id` | string | Research ID |
| `state` | string | `running`, `completed`, or `failed` |
| `done` | bool | Whether research is complete |
| `notes` | array | Research notes/progress updates |

---

### NotebookLM

| Endpoint | Method | Description |
|---|---|---|
| `GET /v1/notebooklm/notebooks` | GET | List notebooks |
| `POST /v1/notebooklm/notebooks` | POST | Create a notebook |
| `GET /v1/notebooklm/notebooks/{id}` | GET | Get notebook details |
| `DELETE /v1/notebooklm/notebooks/{id}` | DELETE | Delete a notebook |
| `GET /v1/notebooklm/notebooks/{id}/sources` | GET | List sources |
| `POST /v1/notebooklm/notebooks/{id}/sources` | POST | Add a source |
| `DELETE /v1/notebooklm/notebooks/{id}/sources/{sid}` | DELETE | Delete a source |

| Model IDs |
|---|
| `notebooklm-2-0` |

#### POST `/v1/notebooklm/notebooks` — Request body

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | string | ❌ | Notebook title (default: `"Untitled"`) |

#### POST `/v1/notebooklm/notebooks/{id}/sources` — Request body

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | string | ❌ | `"url"` or `"text"` (default: `"url"`) |
| `value` | string | ✅ | URL or text content to add |

#### POST `/v1/notebooklm/chat/completions` — Additional fields

When sending a chat completion to NotebookLM, include these extra fields alongside the standard request body:

| Field | Type | Required | Description |
|---|---|---|---|
| `notebook_id` | string | ❌* | Target notebook ID |
| `source_ids` | array | ❌ | Optional list of source IDs to restrict answers to |

\*Required unless `NOTEBOOKLM_DEFAULT_NOTEBOOK_ID` is set.

The last message in `messages` is used as the question.

---

### System

| Endpoint | Method | Description |
|---|---|---|
| `GET /health` | GET | Health check (shows provider connection status) |
| `GET /` | GET | Redirects to Swagger UI (`/docs`) |

## Quick Examples

### DeepSeek

```bash
curl -s http://localhost:8000/v1/deepseek/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-v3",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### Gemini

```bash
curl -s http://localhost:8000/v1/gemini/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-flash",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### NotebookLM

```bash
curl -s http://localhost:8000/v1/notebooklm/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "notebooklm-2-0",
    "messages": [{"role": "user", "content": "Summarize the sources"}],
    "notebook_id": "your-notebook-id-here"
  }'
```

### Streaming

```bash
curl -s -N http://localhost:8000/v1/deepseek/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-v3",
    "messages": [{"role": "user", "content": "Count to 5"}],
    "stream": true
  }'
```

### Gemini — Chat history & deep research

```bash
# List chats
curl -s http://localhost:8000/v1/gemini/chats

# Create a research plan
curl -s -X POST http://localhost:8000/v1/gemini/research/plan \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Latest advances in AI 2026"}'

# Check research status
curl -s http://localhost:8000/v1/gemini/research/<research_id>/status
```

### NotebookLM — Manage notebooks & sources

```bash
# List notebooks
curl -s http://localhost:8000/v1/notebooklm/notebooks

# Create a notebook
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks \
  -H "Content-Type: application/json" \
  -d '{"title": "My Research"}'

# Add a URL source
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/sources \
  -H "Content-Type: application/json" \
  -d '{"type": "url", "value": "https://example.com"}'

# Add a text source
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/sources \
  -H "Content-Type: application/json" \
  -d '{"type": "text", "value": "Some text content here"}'

# Delete a source
curl -s -X DELETE http://localhost:8000/v1/notebooklm/notebooks/<id>/sources/<source_id>

# Delete a notebook
curl -s -X DELETE http://localhost:8000/v1/notebooklm/notebooks/<id>
```
