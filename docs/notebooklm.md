# NotebookLM

## Credentials

NotebookLM uses browser-based authentication. Install the CLI and log in:

```bash
pip install notebooklm-py
notebooklm login
```

This opens a browser for Google sign-in and creates a `storage_state.json` file.

Default location: `~/.notebooklm/profiles/default/storage_state.json`

## Environment

| Env var | Required | Description |
|---|---|---|
| `NOTEBOOKLM_STORAGE_PATH` | ✅ | Path to `storage_state.json` from `notebooklm login` |
| `NOTEBOOKLM_DEFAULT_NOTEBOOK_ID` | ✅ | Target notebook ID — used by all endpoints |

> All endpoints use `NOTEBOOKLM_DEFAULT_NOTEBOOK_ID` automatically. No need to pass a notebook ID in requests.

## Route Overview

All paths are prefixed with `/v1/notebooklm`.

| Category | Endpoints |
|---|---|
| Models | 1 |
| Chat | 7 |
| Artifacts (media) | 7 (see [notebooklm-artifacts.md](notebooklm-artifacts.md)) |

---

## Models

| Endpoint | Method | Description |
|---|---|---|
| `/v1/notebooklm/models` | GET | List available models |

---

## Chat

| Endpoint | Method | Description |
|---|---|---|
| `/v1/notebooklm/chat/completions` | POST | Ask a question (source-grounded Q&A) |
| `/v1/notebooklm/chat/conversation-id` | GET | Get most recent conversation ID |
| `/v1/notebooklm/chat/history` | GET | Get Q&A history |
| `/v1/notebooklm/chat/conversations/{cid}/turns` | GET | Get conversation turns |
| `/v1/notebooklm/chat/conversations/{cid}` | DELETE | Delete a conversation |
| `/v1/notebooklm/chat/configure` | POST | Configure chat persona |
| `/v1/notebooklm/chat/mode` | POST | Set chat mode |

### Chat Completions — Request body

| Field | Type | Required | Description |
|---|---|---|---|
| `model` | string | ❌ | `notebooklm-2-0` (default) |
| `messages` | array | ✅ | Last message is used as the question |
| `stream` | bool | ❌ | Enable SSE streaming |

### `POST /v1/notebooklm/chat/configure` — Request body

| Field | Type | Required | Description |
|---|---|---|---|
| `goal` | string | ❌ | `default`, `custom`, `learning_guide` |
| `response_length` | string | ❌ | `default`, `longer`, `shorter` |
| `custom_prompt` | string | ❌ | Custom instructions (required if goal=custom) |

### `POST /v1/notebooklm/chat/mode` — Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `mode` | string | ❌ | `default` | `default`, `learning_guide`, `concise`, `detailed` |

---

## Artifacts (Media)

See [notebooklm-artifacts.md](notebooklm-artifacts.md) for the complete reference.

Supported media types: **Audio** (podcast/Deep Dive), **Video**, **Cinematic Video**.

---

## Model IDs

| Model | Description |
|---|---|
| `notebooklm-2-0` | Source-grounded Q&A with Google's Gemini models |

---

## Examples

### Chat

```bash
# Basic chat
curl -s http://localhost:8000/v1/notebooklm/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "notebooklm-2-0",
    "messages": [{"role": "user", "content": "Summarize the sources"}]
  }'

# Streaming
curl -s http://localhost:8000/v1/notebooklm/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "notebooklm-2-0",
    "messages": [{"role": "user", "content": "Explain this"}],
    "stream": true
  }'

# Get recent conversation ID
curl -s http://localhost:8000/v1/notebooklm/chat/conversation-id

# Get chat history
curl -s "http://localhost:8000/v1/notebooklm/chat/history?limit=50"

# Configure chat persona
curl -s -X POST http://localhost:8000/v1/notebooklm/chat/configure \
  -H "Content-Type: application/json" \
  -d '{"goal": "learning_guide", "response_length": "longer"}'

# Delete a conversation
curl -s -X DELETE http://localhost:8000/v1/notebooklm/chat/conversations/<cid>
```

### Artifacts

See [notebooklm-artifacts.md](notebooklm-artifacts.md) for all artifact examples.
