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

## Provider-specific Endpoints

### Notebooks

| Endpoint | Method | Description |
|---|---|---|
| `/v1/notebooklm/notebooks` | GET | List all notebooks |
| `/v1/notebooklm/notebooks` | POST | Create a notebook |
| `/v1/notebooklm/notebooks/{id}` | GET | Get notebook details |
| `/v1/notebooklm/notebooks/{id}` | DELETE | Delete a notebook |

#### `POST /v1/notebooklm/notebooks` — Request body

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | string | ❌ | Notebook title (default: `"Untitled"`) |

### Sources

| Endpoint | Method | Description |
|---|---|---|
| `/v1/notebooklm/notebooks/{id}/sources` | GET | List sources in a notebook |
| `/v1/notebooklm/notebooks/{id}/sources` | POST | Add a source to a notebook |
| `/v1/notebooklm/notebooks/{id}/sources/{sid}` | DELETE | Delete a source |

#### `POST /v1/notebooklm/notebooks/{id}/sources` — Request body

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | string | ❌ | `"url"` or `"text"` (default: `"url"`) |
| `value` | string | ✅ | URL or text content to add |

### Chat Completions — Additional fields

Beyond the [common fields](../README.md#common-openai-compatible), NotebookLM chat completions require:

| Field | Type | Required | Description |
|---|---|---|---|
| `notebook_id` | string | ❌* | Target notebook ID |
| `source_ids` | array | ❌ | Restrict answers to specific source IDs |

\*Required unless `NOTEBOOKLM_DEFAULT_NOTEBOOK_ID` is set.

The last message in `messages` is used as the question.

## Model IDs

| Model | Description |
|---|---|
| `notebooklm-2-0` | Source-grounded Q&A with Google's Gemini models |

## Examples

```bash
# Chat with a notebook
curl -s http://localhost:8000/v1/notebooklm/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "notebooklm-2-0",
    "messages": [{"role": "user", "content": "Summarize the sources"}],
    "notebook_id": "your-notebook-id-here"
  }'

# List notebooks
curl -s http://localhost:8000/v1/notebooklm/notebooks

# Create a notebook
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks \
  -H "Content-Type: application/json" \
  -d '{"title": "My Research"}'

# Get notebook details
curl -s http://localhost:8000/v1/notebooklm/notebooks/<notebook_id>

# Delete a notebook
curl -s -X DELETE http://localhost:8000/v1/notebooklm/notebooks/<notebook_id>

# List sources
curl -s http://localhost:8000/v1/notebooklm/notebooks/<id>/sources

# Add a URL source
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/sources \
  -H "Content-Type: application/json" \
  -d '{"type": "url", "value": "https://example.com"}'

# Add text as a source
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/sources \
  -H "Content-Type: application/json" \
  -d '{"type": "text", "value": "Some text content here"}'

# Delete a source
curl -s -X DELETE http://localhost:8000/v1/notebooklm/notebooks/<id>/sources/<source_id>
```
