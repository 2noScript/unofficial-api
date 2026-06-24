# DeepSeek

## Credentials

1. Go to https://chat.deepseek.com and sign in
2. Open DevTools (F12) → **Application** → **Cookies** → `https://chat.deepseek.com`
3. Copy the cookie values:

| Cookie name | Env var | Required |
|---|---|---|
| `ds_session_id` | `DEEPSEEK_SESSION_ID` | ✅ |
| `authorization` | `DEEPSEEK_AUTH_TOKEN` | ✅ |

Or use **Cookie-Editor** extension to export all cookies at once.

## Model IDs

| Model | Description |
|---|---|
| `deepseek-v3` | Fast responses without extended thinking |
| `deepseek-r1` | Reasoning model with extended thinking |
| `deepseek-v4` | Expert model without extended thinking |
| `deepseek-r4` | Expert reasoning model with extended thinking |

> **Note**: V4/R4 expert mode (`model_type="expert"`) is unsupported by the API — falls back to default mode automatically.

## Endpoints

DeepSeek has no provider-specific endpoints. Only the [common OpenAI-compatible endpoints](../README.md#common-openai-compatible) (`/models`, `/chat/completions`).

## Examples

```bash
# Basic chat
curl -s http://localhost:8000/v1/deepseek/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-v3",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# Streaming
curl -s -N http://localhost:8000/v1/deepseek/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-v3",
    "messages": [{"role": "user", "content": "Count to 5"}],
    "stream": true
  }'
```
