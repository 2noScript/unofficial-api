# Gemini

## Credentials

1. Go to https://gemini.google.com and sign in
2. Open DevTools (F12) → **Application** → **Cookies** → `https://gemini.google.com`
3. Copy the cookie values:

| Cookie name | Env var | Required |
|---|---|---|
| `__Secure-1PSID` | `GEMINI_SECURE_1PSID` | ✅ |
| `__Secure-1PSIDTS` | `GEMINI_SECURE_1PSIDTS` | ❌ (account-dependent) |

> Cookies expire. Re-extract them when requests start failing.

## Environment

| Env var | Required | Description |
|---|---|---|
| `GEMINI_SECURE_1PSID` | ✅ | `__Secure-1PSID` cookie value |
| `GEMINI_SECURE_1PSIDTS` | ❌ | `__Secure-1PSIDTS` cookie value (optional, some accounts need it) |

## Provider-specific Endpoints

### Chats

| Endpoint | Method | Description |
|---|---|---|
| `/v1/gemini/chats` | GET | List chat sessions |
| `/v1/gemini/chats/{cid}` | GET | Get chat history |
| `/v1/gemini/chats/{cid}` | DELETE | Delete chat session |
| `/v1/gemini/chats/{cid}/latest-response` | GET | Get latest model response in a chat |

### Gems

| Endpoint | Method | Description |
|---|---|---|
| `/v1/gemini/gems` | GET | List all gems |
| `/v1/gemini/gems` | POST | Create a custom gem |
| `/v1/gemini/gems/{gem_id}` | PATCH | Update a gem |
| `/v1/gemini/gems/{gem_id}` | DELETE | Delete a gem |

#### `POST /v1/gemini/gems` — Request body

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | ✅ | Gem name |
| `prompt` | string | ✅ | System prompt |
| `description` | string | ❌ | Optional description |

#### `PATCH /v1/gemini/gems/{gem_id}` — Request body

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | ✅ | New gem name |
| `prompt` | string | ✅ | New system prompt |
| `description` | string | ❌ | New description |

### Deep Research

| Endpoint | Method | Description |
|---|---|---|
| `/v1/gemini/research/plan` | POST | Create a deep research plan |
| `/v1/gemini/research/start` | POST | Start a deep research |
| `/v1/gemini/research/full` | POST | One-shot research (plan→start→wait) |
| `/v1/gemini/research/{id}/status` | GET | Get research status |

#### `POST /v1/gemini/research/full` — Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `prompt` | string | ✅ | — | Research topic or question |
| `model` | string | ❌ | auto | Model override |
| `poll_interval` | float | ❌ | 10.0 | Seconds between status polls |
| `timeout` | float | ❌ | 600.0 | Max seconds to wait |

#### `POST /v1/gemini/research/plan` — Request body

| Field | Type | Required | Description |
|---|---|---|---|
| `prompt` | string | ✅ | Research topic or question |
| `model` | string | ❌ | Model override |

#### Response

| Field | Type | Description |
|---|---|---|
| `plan` | object | `{research_id, title, query, steps, eta_text, confirm_prompt, cid}` |
| `response_text` | string | Full model response |

#### `POST /v1/gemini/research/start` — Request body

| Field | Type | Required | Description |
|---|---|---|---|
| `plan` | object | ✅ | Plan object from `/research/plan` response |
| `confirm_prompt` | string | ❌ | Override confirmation prompt |

#### `GET /v1/gemini/research/{id}/status` — Response

| Field | Type | Description |
|---|---|---|
| `research_id` | string | Research ID |
| `state` | string | `running`, `completed`, or `failed` |
| `done` | bool | Whether research is complete |
| `title` | string | Research title |
| `query` | string | Original query |
| `cid` | string | Chat session ID |
| `notes` | array | Progress updates |

### Chat Completions — Additional fields

Beyond the [common fields](../README.md#common-openai-compatible), Gemini chat completions support:

| Field | Type | Required | Description |
|---|---|---|---|
| `files` | array | ❌ | File paths to attach (images, PDFs, etc.) |

> Thinking models return `reasoning_content` in `choices[].message`.

## Examples

```bash
# Basic chat
curl -s http://localhost:8000/v1/gemini/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-flash",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# Attach files
curl -s http://localhost:8000/v1/gemini/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-flash",
    "messages": [{"role": "user", "content": "What is in this image?"}],
    "files": ["/path/to/image.jpg"]
  }'

# List chats
curl -s http://localhost:8000/v1/gemini/chats

# Get chat history
curl -s http://localhost:8000/v1/gemini/chats/<cid>

# Delete a chat
curl -s -X DELETE http://localhost:8000/v1/gemini/chats/<cid>

# List gems
curl -s http://localhost:8000/v1/gemini/gems

# Create a gem
curl -s -X POST http://localhost:8000/v1/gemini/gems \
  -H "Content-Type: application/json" \
  -d '{"name": "Assistant", "prompt": "You are a helpful assistant"}'

# Create a research plan
curl -s -X POST http://localhost:8000/v1/gemini/research/plan \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Latest advances in AI 2026"}'

# Start research
curl -s -X POST http://localhost:8000/v1/gemini/research/start \
  -H "Content-Type: application/json" \
  -d '{"plan": {"research_id": "...", "cid": "..."}}'

# Check research status
curl -s http://localhost:8000/v1/gemini/research/<research_id>/status
```
