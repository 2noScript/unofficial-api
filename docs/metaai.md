# Meta AI

## Credentials

1. Go to https://meta.ai and sign in
2. Open DevTools (F12) → **Network** tab → reload → click any request to `meta.ai`
3. In **Request Headers**, find the `Cookie:` line and copy the entire value.

| Cookies needed | Env var | Required |
|---|---|---|
| `datr` + `abra_sess` + `ecto_1_sess` | `META_AI_COOKIE` | ✅ |

## Environment

| Env var | Required | Description |
|---|---|---|
| `META_AI_COOKIE` | ✅ | Full cookie string: `datr=xxx; abra_sess=yyy; ecto_1_sess=zzz` |

## Endpoints

### Common (OpenAI-compatible)

| Endpoint | Method | Description |
|---|---|---|
| `/v1/metaai/models` | GET | List models |
| `/v1/metaai/chat/completions` | POST | Chat completion (stream + non-stream) |

### Provider-specific

| Endpoint | Method | Description |
|---|---|---|
| `/v1/metaai/images/generations` | POST | Generate image from text prompt |
| `/v1/metaai/images/upload` | POST | Upload an image to Meta AI |
| `/v1/metaai/videos/generations` | POST | Generate video from text prompt |
| `/v1/metaai/videos/extend` | POST | Extend an existing generated video |
| `/v1/metaai/media/{id}` | GET | Get media details by ID |
| `/v1/metaai/media/{id}/status` | GET | Get media processing status |

### `POST /v1/metaai/images/generations` — Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `prompt` | string | ✅ | — | Text description of the image |
| `orientation` | string | ❌ | `VERTICAL` | `VERTICAL`, `HORIZONTAL`, `LANDSCAPE`, or `SQUARE` |
| `n` | int | ❌ | `1` | Number of images to generate |

### `POST /v1/metaai/images/upload` — Multipart form

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | ✅ | Image file to upload (PNG, JPG, etc.) |

### `POST /v1/metaai/videos/generations` — Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `prompt` | string | ✅ | — | Text description of the video |
| `auto_poll` | bool | ❌ | `true` | Wait for video to finish generating |

### `POST /v1/metaai/videos/extend` — Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `media_id` | string | ✅ | — | Media ID of the video to extend |
| `auto_poll` | bool | ❌ | `true` | Wait for extension to complete |

## Model IDs

| Model | Description |
|---|---|
| `llama-4` | Llama 4 via Meta AI (chat + image gen + video gen) |

## Examples

```bash
# Chat
curl -s http://localhost:8000/v1/metaai/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-4",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# Generate image
curl -s -X POST http://localhost:8000/v1/metaai/images/generations \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A beautiful sunset over mountains",
    "orientation": "HORIZONTAL"
  }'

# Upload image
curl -s -X POST http://localhost:8000/v1/metaai/images/upload \
  -F "file=@photo.jpg"

# Generate video
curl -s -X POST http://localhost:8000/v1/metaai/videos/generations \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A rocket launching into space",
    "auto_poll": true
  }'

# Extend video
curl -s -X POST http://localhost:8000/v1/metaai/videos/extend \
  -H "Content-Type: application/json" \
  -d '{"media_id": "your-media-id", "auto_poll": true}'

# Get media details
curl -s http://localhost:8000/v1/metaai/media/<media_id>

# Get media status
curl -s http://localhost:8000/v1/metaai/media/<media_id>/status
```
