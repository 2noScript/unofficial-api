# Grok

## Credentials

1. Go to https://grok.com and sign in
2. Open DevTools (F12) → **Application** → **Cookies** → `https://grok.com`
3. Copy the `sso` cookie value (the full value, e.g. `sso=xxx`)

| Env var | Required | Description |
|---|---|---|---|
| `GROK_PROXY_CF_COOKIES` | ✅ | Full cookie string from grok.com (includes `sso`, `sso-rw`, `cf_clearance`, etc.) |
| `GROK_PROXY_USER_AGENT` | ✅ | User-Agent header (must match browser version, e.g. Chrome/136) |
| `GROK_PROXY_BROWSER` | ✅ | curl_cffi impersonation profile (e.g. `chrome136`) |

> Cookies expire. Re-extract them when requests start failing.

## Endpoints

Grok has no provider-specific endpoints. Only the [common OpenAI-compatible endpoints](../README.md#common-openai-compatible) (`/models`, `/chat/completions`).

## Model IDs

All models from the [grok2api registry](https://github.com/2noscript/grok2api/blob/main/app/control/model/registry.py) are available (15+ models).

## Examples

```bash
# Basic chat
curl -s http://localhost:8000/v1/grok/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "grok-4.20-auto",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# Streaming
curl -s -N http://localhost:8000/v1/grok/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "grok-4.20-auto",
    "messages": [{"role": "user", "content": "Count to 5"}],
    "stream": true
  }'
```
