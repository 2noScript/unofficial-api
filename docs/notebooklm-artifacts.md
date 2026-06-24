# NotebookLM Artifacts

Artifacts are AI-generated media content based on notebook sources. Supported types: **Audio** (podcast), **Video**, and **Cinematic Video**.

All paths are prefixed with `/v1/notebooklm`. The notebook is determined automatically by `NOTEBOOKLM_DEFAULT_NOTEBOOK_ID` in `.env`.

---

## Common Behavior

### Generation Request (shared fields)

All generate endpoints accept these optional fields:

| Field | Type | Default | Description |
|---|---|---|---|
| `source_ids` | array | all sources | Restrict to specific source IDs |
| `language` | string | `"en"` | Output language code |
| `instructions` | string | — | Free-text generation instructions |

### Generation Status Response

Create endpoints return immediately with a status object. Poll `GET /artifacts/{task_id}/status` for the result.

```json
{
  "task_id": "abc123",
  "status": "PENDING",
  "url": null,
  "error": null,
  "error_code": null
}
```

Status values: `PROCESSING`, `PENDING`, `COMPLETED`, `FAILED`.

---

## Generate Endpoints

### Audio (`POST /artifacts/generate/audio`)

| Extra Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `audio_format` | string | ❌ | — | `deep_dive`, `brief`, `critique`, `debate` |
| `audio_length` | string | ❌ | — | `short`, `default`, `long` |

### Video (`POST /artifacts/generate/video`)

| Extra Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `video_format` | string | ❌ | — | `explainer`, `brief`, `cinematic` |
| `video_style` | string | ❌ | — | `auto_select`, `classic`, `whiteboard`, `anime`, etc. |
| `style_prompt` | string | ❌ | — | Custom style prompt (requires `video_style=custom`) |

### Cinematic Video (`POST /artifacts/generate/cinematic-video`)

No extra fields. Generates a cinematic (movie-trailer-style) video overview.

---

## Status / Wait

| Endpoint | Method | Description |
|---|---|---|
| `/artifacts/{task_id}/status` | GET | Poll generation status |
| `/artifacts/{task_id}/wait` | POST | Wait for completion (long-poll) |

### `POST /artifacts/{task_id}/wait` — Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `timeout` | float | ❌ | 300.0 | Max seconds to wait |
| `initial_interval` | float | ❌ | 2.0 | Initial poll interval |
| `max_interval` | float | ❌ | 10.0 | Max poll interval |

---

## Download

| Endpoint | Method | Format |
|---|---|---|
| `/artifacts/{artifact_id}/download/audio` | GET | mp3/wav CDN URL |
| `/artifacts/{artifact_id}/download/video` | GET | mp4 CDN URL |

Response:
```json
{
  "url": "https://notebooklm.google.com/...",
  "format": "mp3",
  "content": null
}
```

---

## Examples

```bash
# Generate audio (Deep Dive)
curl -s -X POST http://localhost:8000/v1/notebooklm/artifacts/generate/audio \
  -H "Content-Type: application/json" \
  -d '{"audio_format": "deep_dive", "audio_length": "default"}'

# Generate video
curl -s -X POST http://localhost:8000/v1/notebooklm/artifacts/generate/video \
  -H "Content-Type: application/json" \
  -d '{"video_format": "explainer", "video_style": "classic"}'

# Generate cinematic video
curl -s -X POST http://localhost:8000/v1/notebooklm/artifacts/generate/cinematic-video \
  -H "Content-Type: application/json" \
  -d '{}'

# Poll generation status
curl -s http://localhost:8000/v1/notebooklm/artifacts/<task_id>/status

# Wait for completion
curl -s -X POST http://localhost:8000/v1/notebooklm/artifacts/<task_id>/wait \
  -H "Content-Type: application/json" \
  -d '{"timeout": 300}'

# Download audio
curl -s http://localhost:8000/v1/notebooklm/artifacts/<artifact_id>/download/audio

# Download video
curl -s http://localhost:8000/v1/notebooklm/artifacts/<artifact_id>/download/video
```
