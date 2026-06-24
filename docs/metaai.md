# Meta AI

## Credentials

1. Go to https://meta.ai and sign in
2. Open DevTools (F12) → **Application** → **Cookies** → `https://www.meta.ai`
3. Copy the cookie values:

| Cookie name | Env var | Required |
|---|---|---|
| `datr` | `META_AI_DATR` | ✅ |
| `ecto_1_sess` | `META_AI_ECTO_1_SESS` | ❌ (needed for generation) |
| `abra_sess` | `META_AI_ABRA_SESS` | ❌ (optional, region-dependent) |

## Environment

| Env var | Required | Description |
|---|---|---|
| `META_AI_DATR` | ✅ | `datr` cookie from meta.ai |
| `META_AI_ECTO_1_SESS` | ❌ | `ecto_1_sess` cookie (needed for image/video gen) |
| `META_AI_ABRA_SESS` | ❌ | `abra_sess` cookie (optional) |

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
| `/v1/metaai/videos/generations` | POST | Generate video from text prompt |

### `POST /v1/metaai/images/generations` — Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `prompt` | string | ✅ | — | Text description of the image |
| `orientation` | string | ❌ | `VERTICAL` | `VERTICAL`, `HORIZONTAL`, `LANDSCAPE`, or `SQUARE` |
| `n` | int | ❌ | `1` | Number of images to generate |

### `POST /v1/metaai/videos/generations` — Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `prompt` | string | ✅ | — | Text description of the video |
| `auto_poll` | bool | ❌ | `true` | Wait for video to finish generating |

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

# Generate video
curl -s -X POST http://localhost:8000/v1/metaai/videos/generations \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A rocket launching into space",
    "auto_poll": true
  }'
```
