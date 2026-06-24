# NotebookLM Artifacts

Artifacts are AI-generated media content based on notebook sources. Supported types: **Audio** (podcast), **Video**, and **Cinematic Video**.

All paths are prefixed with `/v1/notebooklm`.

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

### Audio (`POST /notebooks/{id}/artifacts/generate/audio`)

| Extra Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `audio_format` | string | ❌ | — | `deep_dive`, `brief`, `critique`, `debate` |
| `audio_length` | string | ❌ | — | `short`, `default`, `long` |

Generates a podcast-style Deep Dive or similar audio overview.

### Video (`POST /notebooks/{id}/artifacts/generate/video`)

| Extra Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `video_format` | string | ❌ | — | `explainer`, `brief`, `cinematic` |
| `video_style` | string | ❌ | — | `auto_select`, `classic`, `whiteboard`, `anime`, etc. |
| `style_prompt` | string | ❌ | — | Custom style prompt (requires `video_style=custom`) |

### Cinematic Video (`POST /notebooks/{id}/artifacts/generate/cinematic-video`)

No extra fields. Generates a cinematic (movie-trailer-style) video overview.

---

## Status / Wait

| Endpoint | Method | Description |
|---|---|---|
| `/notebooks/{id}/artifacts/{task_id}/status` | GET | Poll generation status |
| `/notebooks/{id}/artifacts/{task_id}/wait` | POST | Wait for completion (long-poll) |

### `POST /notebooks/{id}/artifacts/{task_id}/wait` — Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `timeout` | float | ❌ | 300.0 | Max seconds to wait |
| `initial_interval` | float | ❌ | 2.0 | Initial poll interval |
| `max_interval` | float | ❌ | 10.0 | Max poll interval |

---

## Download

Download endpoints return a CDN URL for the generated media.

```json
{
  "url": "https://notebooklm.google.com/...",
  "format": "mp3",
  "content": null
}
```

| Endpoint | Method | Format |
|---|---|---|
| `/notebooks/{id}/artifacts/{aid}/download/audio` | GET | mp3/wav |
| `/notebooks/{id}/artifacts/{aid}/download/video` | GET | mp4 |

---

## Examples

```bash
# Generate audio (Deep Dive)
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts/generate/audio \
  -H "Content-Type: application/json" \
  -d '{"audio_format": "deep_dive", "audio_length": "default"}'

# Generate video
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts/generate/video \
  -H "Content-Type: application/json" \
  -d '{"video_format": "explainer", "video_style": "classic"}'

# Generate cinematic video
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts/generate/cinematic-video \
  -H "Content-Type: application/json" \
  -d '{}'

# Poll generation status
curl -s http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts/<task_id>/status

# Wait for completion
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts/<task_id>/wait \
  -H "Content-Type: application/json" \
  -d '{"timeout": 300}'

# Download audio
curl -s http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts/<aid>/download/audio

# Download video
curl -s http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts/<aid>/download/video
```
