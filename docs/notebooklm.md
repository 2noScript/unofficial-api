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
| `NOTEBOOKLM_STORAGE_PATH` | ✅* | Path to `storage_state.json` from `notebooklm login` |
| `NOTEBOOKLM_DEFAULT_NOTEBOOK_ID` | ❌ | Default notebook ID for `/chat/completions` |

\*Required for any NotebookLM endpoint.

## Route Overview

All paths are prefixed with `/v1/notebooklm`.

| Category | Endpoints |
|---|---|
| Models | 1 (`GET /models`) |
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
| `/v1/notebooklm/notebooks/{id}/chat/conversation-id` | GET | Get most recent conversation ID |
| `/v1/notebooklm/notebooks/{id}/chat/history` | GET | Get Q&A history |
| `/v1/notebooklm/notebooks/{id}/chat/conversations/{cid}/turns` | GET | Get conversation turns |
| `/v1/notebooklm/notebooks/{id}/chat/conversations/{cid}` | DELETE | Delete a conversation |
| `/v1/notebooklm/notebooks/{id}/chat/configure` | POST | Configure chat persona |
| `/v1/notebooklm/notebooks/{id}/chat/mode` | POST | Set chat mode |

### Chat Completions — Additional fields

| Field | Type | Required | Description |
|---|---|---|---|
| `notebook_id` | string | ❌* | Target notebook ID |
| `source_ids` | array | ❌ | Restrict answers to specific source IDs |
| `conversation_id` | string | ❌ | Continue an existing conversation |

\*Required unless `NOTEBOOKLM_DEFAULT_NOTEBOOK_ID` is set. The last message in `messages` is used as the question.

### `POST /v1/notebooklm/notebooks/{id}/chat/configure` — Request body

| Field | Type | Required | Description |
|---|---|---|---|
| `goal` | string | ❌ | `default`, `custom`, `learning_guide` |
| `response_length` | string | ❌ | `default`, `longer`, `shorter` |
| `custom_prompt` | string | ❌ | Custom instructions (required if goal=custom) |

### `POST /v1/notebooklm/notebooks/{id}/chat/mode` — Request body

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
    "messages": [{"role": "user", "content": "Summarize the sources"}],
    "notebook_id": "your-notebook-id"
  }'

# Chat with conversation tracking
curl -s http://localhost:8000/v1/notebooklm/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "notebooklm-2-0",
    "messages": [{"role": "user", "content": "Tell me more"}],
    "notebook_id": "your-notebook-id",
    "conversation_id": "previous-conversation-id"
  }'

# Streaming
curl -s http://localhost:8000/v1/notebooklm/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "notebooklm-2-0",
    "messages": [{"role": "user", "content": "Explain this"}],
    "notebook_id": "your-notebook-id",
    "stream": true
  }'

# Get recent conversation ID
curl -s http://localhost:8000/v1/notebooklm/notebooks/<id>/chat/conversation-id

# Get chat history
curl -s "http://localhost:8000/v1/notebooklm/notebooks/<id>/chat/history?limit=50"

# Configure chat persona
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/chat/configure \
  -H "Content-Type: application/json" \
  -d '{"goal": "learning_guide", "response_length": "longer"}'

# Delete a conversation
curl -s -X DELETE http://localhost:8000/v1/notebooklm/notebooks/<id>/chat/conversations/<cid>
```

### Artifacts

See [notebooklm-artifacts.md](notebooklm-artifacts.md) for all artifact examples.
