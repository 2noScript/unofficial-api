# Grok

## Credentials

1. Go to https://grok.com and sign in
2. Open DevTools (F12) → **Application** → **Cookies** → `https://grok.com`
3. Copy the cookie values:

| Cookie name | Env var | Required |
|---|---|---|
| `sso` | `GROK_SSO` | ✅ |
| `sso-rw` | `GROK_SSO_RW` | ✅ |

> Cookies expire. Re-extract them when requests start failing.

## Environment

| Env var | Required | Description |
|---|---|---|
| `GROK_SSO` | ✅ | `sso` cookie from grok.com |
| `GROK_SSO_RW` | ✅ | `sso-rw` cookie from grok.com |

## Endpoints

Grok has no provider-specific endpoints. Only the [common OpenAI-compatible endpoints](../README.md#common-openai-compatible) (`/models`, `/chat/completions`).

## Model IDs

| Model | Description |
|---|---|
| `grok-3` | Grok 3 via xAI (chat with optional web search) |

## Examples

```bash
# Basic chat
curl -s http://localhost:8000/v1/grok/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "grok-3",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# Streaming
curl -s -N http://localhost:8000/v1/grok/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "grok-3",
    "messages": [{"role": "user", "content": "Count to 5"}],
    "stream": true
  }'
```
