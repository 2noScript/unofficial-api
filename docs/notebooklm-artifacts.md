# NotebookLM Artifacts

Artifacts are AI-generated content based on notebook sources. There are 11 artifact types: Audio, Video, Report, Study Guide, Quiz, Flashcards, Infographic, Slide Deck, Data Table, Mind Map, and Cinematic Video.

Artifacts API (~32 endpoints) is under `POST /v1/notebooklm/notebooks/{id}/artifacts/...`.

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

### Report (`POST /notebooks/{id}/artifacts/generate/report`)

| Extra Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `report_format` | string | ❌ | `briefing_doc` | `briefing_doc`, `study_guide`, `blog_post`, `custom` |
| `custom_prompt` | string | ❌ | — | Custom report prompt (for `custom` format) |
| `extra_instructions` | string | ❌ | — | Extra instructions |

### Study Guide (`POST /notebooks/{id}/artifacts/generate/study-guide`)

| Extra Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `extra_instructions` | string | ❌ | — | Extra instructions |

### Quiz or Flashcards (`POST /notebooks/{id}/artifacts/generate/quiz-flashcards`)

| Extra Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `quantity` | string | ❌ | — | `fewer`, `standard`, `more` |
| `difficulty` | string | ❌ | — | `easy`, `medium`, `hard` |

Generates both quiz questions and flashcards in one call.

### Infographic (`POST /notebooks/{id}/artifacts/generate/infographic`)

| Extra Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `orientation` | string | ❌ | — | `landscape`, `portrait`, `square` |
| `detail_level` | string | ❌ | — | `concise`, `standard`, `detailed` |
| `style` | string | ❌ | — | `auto_select`, `sketch_note`, `professional`, etc. |

### Slide Deck (`POST /notebooks/{id}/artifacts/generate/slide-deck`)

| Extra Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `slide_format` | string | ❌ | — | `detailed_deck`, `presenter_slides` |
| `slide_length` | string | ❌ | — | `default`, `short` |

### Data Table (`POST /notebooks/{id}/artifacts/generate/data-table`)

No extra fields. Generates a CSV-style data table from sources.

### Mind Map (`POST /notebooks/{id}/artifacts/generate/mind-map`)

| Extra Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `wait` | bool | ❌ | `true` | Wait for completion before returning |

Generates a note-backed mind map (returns immediately with `note_id` and `mind_map` object). For interactive mind maps, see the [Mind Maps](../notebooklm.md#mind-maps) section.

---

## Post-Generation Actions

| Endpoint | Method | Description |
|---|---|---|
| `/notebooks/{id}/artifacts/{aid}/status` | GET | Poll generation status |
| `/notebooks/{id}/artifacts/{aid}/wait` | POST | Wait for completion with polling |
| `/notebooks/{id}/artifacts/{aid}/retry` | POST | Retry a failed generation |
| `/notebooks/{id}/artifacts/generate/revise-slide` | POST | Revise a specific slide |
| `/notebooks/{id}/artifacts/generate/suggest-reports` | GET | Get suggested report formats |

### `POST /notebooks/{id}/artifacts/{aid}/wait` — Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `timeout` | float | ❌ | 300.0 | Max seconds to wait |
| `initial_interval` | float | ❌ | 2.0 | Initial poll interval |
| `max_interval` | float | ❌ | 10.0 | Max poll interval |

### `POST /notebooks/{id}/artifacts/generate/revise-slide` — Request body

| Field | Type | Required | Description |
|---|---|---|---|
| `slide_index` | int | ✅ | Index of the slide to revise (0-based) |
| `prompt` | string | ✅ | Revision instructions |

---

## List & Get

| Endpoint | Method | Description |
|---|---|---|
| `/notebooks/{id}/artifacts` | GET | List all artifacts |
| `/notebooks/{id}/artifacts/{aid}` | GET | Get artifact by ID |
| `/notebooks/{id}/artifacts?type={type}` | GET | Filter by type (`audio`, `video`, `report`, `study_guide`, `quiz`, `flashcards`, `infographic`, `slide_deck`, `data_table`, `mind_map`) |

### Artifact Response

```json
{
  "id": "artifact-id",
  "title": "Deep Dive: AI Overview",
  "kind": "audio",
  "status": 3,
  "status_str": "completed",
  "created_at": "2026-06-24T10:00:00",
  "url": "https://notebooklm.google.com/...",
  "report_subtype": null
}
```

Status codes: `1`=processing, `2`=pending, `3`=completed, `4`=failed.

---

## Download

Download endpoints return content differently based on artifact type.

### Media Types (Audio, Video, Infographic, Slide Deck)

Return a CDN download URL:

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
| `/notebooks/{id}/artifacts/{aid}/download/infographic` | GET | png |
| `/notebooks/{id}/artifacts/{aid}/download/slide-deck` | GET | pdf/pptx |

### Structured Types (Report, Quiz, Flashcards, Mind Map, Data Table)

Return inline content (markdown, JSON, CSV):

```json
{
  "url": null,
  "format": "markdown",
  "content": "# Report Title\n\nContent here..."
}
```

| Endpoint | Method | Format |
|---|---|---|
| `/notebooks/{id}/artifacts/{aid}/download/report` | GET | markdown |
| `/notebooks/{id}/artifacts/{aid}/download/quiz` | GET | json |
| `/notebooks/{id}/artifacts/{aid}/download/flashcards` | GET | json |
| `/notebooks/{id}/artifacts/{aid}/download/mind-map` | GET | json |
| `/notebooks/{id}/artifacts/{aid}/download/data-table` | GET | csv |

---

## Management

| Endpoint | Method | Description |
|---|---|---|
| `/notebooks/{id}/artifacts/{aid}` | DELETE | Delete an artifact |
| `/notebooks/{id}/artifacts/{aid}` | PATCH | Rename an artifact |

### `PATCH /notebooks/{id}/artifacts/{aid}` — Request body

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | string | ✅ | New artifact title |

---

## Export

| Endpoint | Method | Description |
|---|---|---|
| `/notebooks/{id}/artifacts/{aid}/export/docs` | POST | Export to Google Docs |
| `/notebooks/{id}/artifacts/{aid}/export/sheets` | POST | Export to Google Sheets (data tables) |

### `POST /notebooks/{id}/artifacts/{aid}/export/docs` — Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `title` | string | ❌ | `"Export"` | Document title |

---

## Examples

```bash
# Generate audio (Deep Dive)
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts/generate/audio \
  -H "Content-Type: application/json" \
  -d '{"audio_format": "deep_dive", "audio_length": "default"}'

# Generate report
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts/generate/report \
  -H "Content-Type: application/json" \
  -d '{"report_format": "briefing_doc", "extra_instructions": "Focus on technical details"}'

# Generate infographic
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts/generate/infographic \
  -H "Content-Type: application/json" \
  -d '{"orientation": "landscape", "detail_level": "standard"}'

# Generate slide deck
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts/generate/slide-deck \
  -H "Content-Type: application/json" \
  -d '{"slide_format": "detailed_deck"}'

# Poll generation status
curl -s http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts/<aid>/status

# Wait for completion
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts/<aid>/wait \
  -H "Content-Type: application/json" \
  -d '{"timeout": 300}'

# Retry failed generation
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts/<aid>/retry

# List all artifacts
curl -s http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts

# List only audio artifacts
curl -s "http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts?type=audio"

# Get artifact details
curl -s http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts/<aid>

# Download audio
curl -s http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts/<aid>/download/audio

# Download report (returns markdown content inline)
curl -s http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts/<aid>/download/report

# Download flashcards (returns JSON)
curl -s http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts/<aid>/download/flashcards

# Rename artifact
curl -s -X PATCH http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts/<aid> \
  -H "Content-Type: application/json" \
  -d '{"title": "New Title"}'

# Delete artifact
curl -s -X DELETE http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts/<aid>

# Revise slide
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts/generate/revise-slide \
  -H "Content-Type: application/json" \
  -d '{"art_id": "<aid>", "slide_index": 2, "prompt": "Add more details to this slide"}'

# Get suggested reports
curl -s http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts/generate/suggest-reports

# Export to Google Docs
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts/<aid>/export/docs \
  -H "Content-Type: application/json" \
  -d '{"title": "My Report"}'

# Export data table to Google Sheets
curl -s -X POST http://localhost:8000/v1/notebooklm/notebooks/<id>/artifacts/<aid>/export/sheets \
  -H "Content-Type: application/json" \
  -d '{"title": "My Data"}'
```

---

## Quick Reference: Generate Type → SDK Mapping

| Endpoint | SDK Method | Returns |
|---|---|---|
| `generate/audio` | `client.artifacts.generate_audio(...)` | `GenerationStatus` |
| `generate/video` | `client.artifacts.generate_video(...)` | `GenerationStatus` |
| `generate/cinematic-video` | `client.artifacts.generate_cinematic_video(...)` | `GenerationStatus` |
| `generate/report` | `client.artifacts.generate_report(...)` | `GenerationStatus` |
| `generate/study-guide` | `client.artifacts.generate_study_guide(...)` | `GenerationStatus` |
| `generate/quiz-flashcards` | `client.artifacts.generate_quiz(...)` / `generate_flashcards(...)` | `GenerationStatus` |
| `generate/infographic` | `client.artifacts.generate_infographic(...)` | `GenerationStatus` |
| `generate/slide-deck` | `client.artifacts.generate_slide_deck(...)` | `GenerationStatus` |
| `generate/data-table` | `client.artifacts.generate_data_table(...)` | `GenerationStatus` |
| `generate/mind-map` | `client.artifacts.generate_mind_map(...)` | `MindMapResult` |
