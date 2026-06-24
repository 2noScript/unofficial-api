# Gemini

## Credentials

1. Go to https://gemini.google.com and sign in
2. Open DevTools (F12) → **Application** → **Cookies** → `https://gemini.google.com`
3. Copy the cookie values:

| Cookie name | Env var | Required |
|---|---|---|
| `__Secure-1PSID` | `GEMINI_SECURE_1PSID` | ✅ |
| `__Secure-1PSIDTS` | `GEMINI_SECURE_1PSIDTS` | ❌ (account-dependent) |

> Cookies expire. Re-extract them when requests start failing.

## Environment

| Env var | Required | Description |
|---|---|---|
| `GEMINI_SECURE_1PSID` | ✅ | `__Secure-1PSID` cookie value |
| `GEMINI_SECURE_1PSIDTS` | ❌ | `__Secure-1PSIDTS` cookie value (optional, some accounts need it) |

## Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/v1/gemini/models` | GET | List available models |
| `/v1/gemini/chat/completions` | POST | Chat completions (streaming supported) |

### Chat Completions — Additional fields

Beyond the common OpenAI-compatible fields, Gemini chat completions support:

| Field | Type | Required | Description |
|---|---|---|---|
| `files` | array | ❌ | File paths to attach (images, PDFs, etc.) |

> Thinking models return `reasoning_content` in `choices[].message`.

## Examples

```bash
# Basic chat
curl -s http://localhost:8000/v1/gemini/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-flash",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# Streaming
curl -s http://localhost:8000/v1/gemini/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-flash",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'

# Attach files
curl -s http://localhost:8000/v1/gemini/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-flash",
    "messages": [{"role": "user", "content": "What is in this image?"}],
    "files": ["/path/to/image.jpg"]
  }'

# List models
curl -s http://localhost:8000/v1/gemini/models
```
