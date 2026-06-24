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

## Route Overview (~84 endpoints)

All paths are prefixed with `/v1/notebooklm`.

| Category | Endpoints | Doc |
|---|---|---|
| Models | 1 (`GET /models`) | — |
| Notebooks | 3 | (below) |
| Chat | 7 | (below) |
| Sources | 14 | (below) |
| Notes | 5 | (below) |
| Artifacts | ~32 | [`notebooklm-artifacts.md`](notebooklm-artifacts.md) |
| Research | 5 | (below) |
| Sharing | 6 | (below) |
| Settings | 4 | (below) |
| Mind Maps | 6 | (below) |

---

## Models

| Endpoint | Method | Description |
|---|---|---|
| `/v1/notebooklm/models` | GET | List available models |

---

## Notebooks

| Endpoint | Method | Description |
|---|---|---|
| `/v1/notebooklm/notebooks` | GET | List all notebooks |
| `/v1/notebooklm/notebooks` | POST | Create a notebook |
| `/v1/notebooklm/notebooks/{id}` | GET | Get notebook details |
| `/v1/notebooklm/notebooks/{id}` | DELETE | Delete a notebook |

### `POST /v1/notebooklm/notebooks` — Request body

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | string | ❌ | Notebook title (default: `"Untitled"`) |

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

Beyond the [common fields](../README.md#common-openai-compatible), NotebookLM chat completions require:

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

## Sources

| Endpoint | Method | Description |
|---|---|---|
| `/v1/notebooklm/notebooks/{id}/sources` | GET | List all sources |
| `/v1/notebooklm/notebooks/{id}/sources` | POST | Add a source (generic) |
| `/v1/notebooklm/notebooks/{id}/sources/url` | POST | Add a URL source |
| `/v1/notebooklm/notebooks/{id}/sources/text` | POST | Add a text source |
| `/v1/notebooklm/notebooks/{id}/sources/file` | POST | Upload a file as source |
| `/v1/notebooklm/notebooks/{id}/sources/drive` | POST | Add a Google Drive source |
| `/v1/notebooklm/notebooks/{id}/sources/{sid}` | GET | Get source details |
| `/v1/notebooklm/notebooks/{id}/sources/{sid}` | PATCH | Rename a source |
| `/v1/notebooklm/notebooks/{id}/sources/{sid}` | DELETE | Delete a source |
| `/v1/notebooklm/notebooks/{id}/sources/{sid}/refresh` | POST | Refresh source content |
| `/v1/notebooklm/notebooks/{id}/sources/{sid}/freshness` | GET | Check if source needs refresh |
| `/v1/notebooklm/notebooks/{id}/sources/{sid}/guide` | GET | Get AI summary + keywords |
| `/v1/notebooklm/notebooks/{id}/sources/{sid}/fulltext` | GET | Get full text content |
| `/v1/notebooklm/notebooks/{id}/sources/{sid}/wait` | POST | Wait for source to become ready |

### `POST /v1/notebooklm/notebooks/{id}/sources` — Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `type` | string | ❌ | `"url"` | `"url"` or `"text"` |
| `value` | string | ✅ | — | URL or text content |

### `POST /v1/notebooklm/notebooks/{id}/sources/url` — Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `url` | string | ✅ | — | Source URL |
| `wait` | bool | ❌ | `false` | Wait for processing to complete |

### `POST /v1/notebooklm/notebooks/{id}/sources/text` — Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `title` | string | ❌ | `"Source"` | Source title |
| `content` | string | ✅ | — | Source content (markdown) |
| `wait` | bool | ❌ | `false` | Wait for processing to complete |
| `idempotent` | bool | ❌ | `false` | Skip if identical text already exists |

### `POST /v1/notebooklm/notebooks/{id}/sources/file` — Multipart form

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | ✅ | File to upload (PDF, text, markdown, EPUB, Word, CSV, images) |
| `title` | string | ❌ | Optional source title |
| `wait` | bool | ❌ | Wait for processing |

### `POST /v1/notebooklm/notebooks/{id}/sources/drive` — Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `file_id` | string | ✅ | — | Google Drive file ID |
| `title` | string | ❌ | `"Drive Source"` | Source title |
| `mime_type` | string | ❌ | `application/vnd.google-apps.document` | Drive file MIME type |
| `wait` | bool | ❌ | `false` | Wait for processing |

### `PATCH /v1/notebooklm/notebooks/{id}/sources/{sid}` — Request body

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | string | ✅ | New source title |

### `POST /v1/notebooklm/notebooks/{id}/sources/{sid}/wait` — Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `timeout` | float | ❌ | 120.0 | Max seconds to wait |
| `initial_interval` | float | ❌ | 1.0 | Initial poll interval |
| `max_interval` | float | ❌ | 10.0 | Max poll interval |

---

## Notes

| Endpoint | Method | Description |
|---|---|---|
| `/v1/notebooklm/notebooks/{id}/notes` | GET | List all notes |
| `/v1/notebooklm/notebooks/{id}/notes` | POST | Create a note |
| `/v1/notebooklm/notebooks/{id}/notes/{nid}` | GET | Get note by ID |
| `/v1/notebooklm/notebooks/{id}/notes/{nid}` | PATCH | Update a note |
| `/v1/notebooklm/notebooks/{id}/notes/{nid}` | DELETE | Delete a note |

### `POST /v1/notebooklm/notebooks/{id}/notes` — Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `title` | string | ❌ | `"New Note"` | Note title |
| `content` | string | ❌ | `""` | Note content (markdown) |

### `PATCH /v1/notebooklm/notebooks/{id}/notes/{nid}` — Request body

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | string | ✅ | New title |
| `content` | string | ✅ | New content (markdown) |

---

## Research

| Endpoint | Method | Description |
|---|---|---|
| `/v1/notebooklm/notebooks/{id}/research/start` | POST | Start a research session |
| `/v1/notebooklm/notebooks/{id}/research/tasks/{tid}` | GET | Poll research task status |
| `/v1/notebooklm/notebooks/{id}/research/tasks/{tid}/wait` | POST | Wait for research to complete |
| `/v1/notebooklm/notebooks/{id}/research/tasks/{tid}/import` | POST | Import research sources into notebook |
| `/v1/notebooklm/notebooks/{id}/research/tasks/{tid}/import-verified` | POST | Import with timeout-tolerant verification |

### `POST /v1/notebooklm/notebooks/{id}/research/start` — Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `query` | string | ✅ | — | Research query |
| `source` | string | ❌ | `"web"` | `"web"` or `"drive"` |
| `mode` | string | ❌ | `"fast"` | `"fast"` or `"deep"` |

### `POST /v1/notebooklm/notebooks/{id}/research/tasks/{tid}/wait` — Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `timeout` | float | ❌ | 1800.0 | Max seconds to wait |
| `interval` | float | ❌ | 5.0 | Poll interval in seconds |

### `POST /v1/notebooklm/notebooks/{id}/research/tasks/{tid}/import` — Request body

| Field | Type | Required | Description |
|---|---|---|---|
| `sources` | array | ✅ | `[{url, title}]` sources to import |

### `POST /v1/notebooklm/notebooks/{id}/research/tasks/{tid}/import-verified` — Request body

Same as `import`, but retries on timeout with exponential backoff.

---

## Sharing

| Endpoint | Method | Description |
|---|---|---|
| `/v1/notebooklm/notebooks/{id}/sharing/status` | GET | Get sharing configuration |
| `/v1/notebooklm/notebooks/{id}/sharing/public` | POST | Enable/disable public link |
| `/v1/notebooklm/notebooks/{id}/sharing/view-level` | POST | Set viewer access level |
| `/v1/notebooklm/notebooks/{id}/sharing/users` | POST | Add a shared user |
| `/v1/notebooklm/notebooks/{id}/sharing/users` | PATCH | Update user permission |
| `/v1/notebooklm/notebooks/{id}/sharing/users?email=` | DELETE | Remove a user |

### `POST /v1/notebooklm/notebooks/{id}/sharing/public` — Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `public` | bool | ❌ | `true` | Enable public link sharing |

### `POST /v1/notebooklm/notebooks/{id}/sharing/view-level` — Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `level` | int | ❌ | 0 | `0`=full_notebook, `1`=chat_only |

### `POST /v1/notebooklm/notebooks/{id}/sharing/users` — Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `email` | string | ✅ | — | User email |
| `permission` | int | ❌ | 3 | `2`=editor, `3`=viewer |
| `notify` | bool | ❌ | `true` | Send notification |
| `welcome_message` | string | ❌ | `""` | Welcome message |

### `PATCH /v1/notebooklm/notebooks/{id}/sharing/users` — Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `email` | string | ✅ | — | User email |
| `permission` | int | ❌ | 3 | `2`=editor, `3`=viewer |

---

## Settings

| Endpoint | Method | Description |
|---|---|---|
| `/v1/notebooklm/settings/output-language` | GET | Get current output language |
| `/v1/notebooklm/settings/output-language` | POST | Set output language |
| `/v1/notebooklm/settings/account-limits` | GET | Get account limits |
| `/v1/notebooklm/settings/account-tier` | GET | Get account subscription tier |

### `POST /v1/notebooklm/settings/output-language` — Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `language` | string | ❌ | `"en"` | Language code (e.g. `en`, `zh_Hans`, `ja`) |

---

## Mind Maps

| Endpoint | Method | Description |
|---|---|---|
| `/v1/notebooklm/notebooks/{id}/mind-maps` | GET | List all mind maps |
| `/v1/notebooklm/notebooks/{id}/mind-maps/{mmid}` | GET | Get mind map by ID |
| `/v1/notebooklm/notebooks/{id}/mind-maps/generate` | POST | Generate a mind map |
| `/v1/notebooklm/notebooks/{id}/mind-maps/{mmid}` | PATCH | Rename a mind map |
| `/v1/notebooklm/notebooks/{id}/mind-maps/{mmid}` | DELETE | Delete a mind map |
| `/v1/notebooklm/notebooks/{id}/mind-maps/{mmid}/tree` | GET | Get node tree |

### `POST /v1/notebooklm/notebooks/{id}/mind-maps/generate` — Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `source_ids` | array | ❌ | all sources | Source IDs to base mind map on |
| `kind` | string | ❌ | `"interactive"` | `"note_backed"` or `"interactive"` |
| `language` | string | ❌ | `"en"` | Language code |
| `instructions` | string | ❌ | — | Custom instructions |
| `wait` | bool | ❌ | `true` | Wait for completion |

### `PATCH /v1/notebooklm/notebooks/{id}/mind-maps/{mmid}` — Request body

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | string | ✅ | New title |
| `kind` | string | ❌ | Kind (auto-detected if omitted) |

---

## Artifacts

See [notebooklm-artifacts.md](notebooklm-artifacts.md) for the complete artifacts reference (~32 endpoints).

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

### Notebooks & Sources

```bash
# List notebooks
curl -s http://localhost:8000/v1/notebooklm/notebooks

# Create notebook
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks \
  -H "Content-Type: application/json" \
  -d '{"title": "My Research"}'

# List sources
curl -s http://localhost:8000/v1/notebooklm/notebooks/<id>/sources

# Add URL source
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/sources/url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "wait": true}'

# Upload file as source
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/sources/file \
  -F "file=@document.pdf" \
  -F "title=My Document" \
  -F "wait=true"

# Get source guide (summary + keywords)
curl -s http://localhost:8000/v1/notebooklm/notebooks/<id>/sources/<sid>/guide

# Get source full text
curl -s http://localhost:8000/v1/notebooklm/notebooks/<id>/sources/<sid>/fulltext

# Rename source
curl -s -X PATCH http://localhost:8000/v1/notebooklm/notebooks/<id>/sources/<sid> \
  -H "Content-Type: application/json" \
  -d '{"title": "New Title"}'

# Delete source
curl -s -X DELETE http://localhost:8000/v1/notebooklm/notebooks/<id>/sources/<sid>
```

### Notes

```bash
# List notes
curl -s http://localhost:8000/v1/notebooklm/notebooks/<id>/notes

# Create note
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/notes \
  -H "Content-Type: application/json" \
  -d '{"title": "Summary", "content": "# Key Points\n- Point 1\n- Point 2"}'

# Update note
curl -s -X PATCH http://localhost:8000/v1/notebooklm/notebooks/<id>/notes/<nid> \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated", "content": "New content"}'

# Delete note
curl -s -X DELETE http://localhost:8000/v1/notebooklm/notebooks/<id>/notes/<nid>
```

### Research

```bash
# Start research
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/research/start \
  -H "Content-Type: application/json" \
  -d '{"query": "Latest AI breakthroughs 2026", "mode": "fast"}'

# Poll research status
curl -s http://localhost:8000/v1/notebooklm/notebooks/<id>/research/tasks/<tid>

# Wait for completion
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/research/tasks/<tid>/wait \
  -H "Content-Type: application/json" \
  -d '{"timeout": 600, "interval": 3}'

# Import sources from research
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/research/tasks/<tid>/import \
  -H "Content-Type: application/json" \
  -d '{"sources": [{"url": "https://example.com", "title": "Example"}]}'
```

### Sharing

```bash
# Get sharing status
curl -s http://localhost:8000/v1/notebooklm/notebooks/<id>/sharing/status

# Enable public link
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/sharing/public \
  -H "Content-Type: application/json" \
  -d '{"public": true}'

# Add a user
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/sharing/users \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "permission": 2}'

# Remove a user
curl -s -X DELETE "http://localhost:8000/v1/notebooklm/notebooks/<id>/sharing/users?email=user@example.com"
```

### Settings

```bash
# Get output language
curl -s http://localhost:8000/v1/notebooklm/settings/output-language

# Set output language
curl -s -X POST http://localhost:8000/v1/notebooklm/settings/output-language \
  -H "Content-Type: application/json" \
  -d '{"language": "zh_Hans"}'

# Get account limits
curl -s http://localhost:8000/v1/notebooklm/settings/account-limits

# Get account tier
curl -s http://localhost:8000/v1/notebooklm/settings/account-tier
```

### Mind Maps

```bash
# List mind maps
curl -s http://localhost:8000/v1/notebooklm/notebooks/<id>/mind-maps

# Generate interactive mind map
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/mind-maps/generate \
  -H "Content-Type: application/json" \
  -d '{"kind": "interactive", "wait": true}'

# Get mind map tree
curl -s http://localhost:8000/v1/notebooklm/notebooks/<id>/mind-maps/<mmid>/tree

# Rename mind map
curl -s -X PATCH http://localhost:8000/v1/notebooklm/notebooks/<id>/mind-maps/<mmid> \
  -H "Content-Type: application/json" \
  -d '{"title": "New Title"}'

# Delete mind map
curl -s -X DELETE http://localhost:8000/v1/notebooklm/notebooks/<id>/mind-maps/<mmid>
```

### Artifacts

See [notebooklm-artifacts.md](notebooklm-artifacts.md) for all artifact examples.
