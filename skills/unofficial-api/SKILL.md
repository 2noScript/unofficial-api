---
name: unofficial-api
description: Entry point for Unofficial API — OpenAI-compatible REST gateway for DeepSeek, Gemini, Grok (xAI), Meta AI (Llama 4), and NotebookLM. Use when the user mentions Unofficial API, UNOFFICIAL_API_URL, or wants AI without writing provider boilerplate. This skill covers setup + indexes capability skills; fetch the relevant capability SKILL.md from the URLs below when needed.
---

# Unofficial API

OpenAI-compatible REST gateway aggregating DeepSeek, Gemini, Grok, Meta AI, and NotebookLM into a single endpoint. One URL, many models.

## Setup

```bash
export UNOFFICIAL_API_URL="http://localhost:8000"      # local or deployed URL
```

All requests: `${UNOFFICIAL_API_URL}/v1/{provider}/chat/completions`.

Verify: `curl $UNOFFICIAL_API_URL/health` → `{"status":"ok"}`.

## Authentication

All chat and model endpoints require an API key. Generate one first (no auth needed to bootstrap):

```bash
curl -X POST $UNOFFICIAL_API_URL/v1/keys/generate \
  -H "Content-Type: application/json" \
  -d '{"name": "my-key"}'
# → {"api_key": "ua-xxxxxxxx-xxxxxx-xxxxxxxx", "name": "my-key"}

export UNOFFICIAL_API_KEY="ua-xxxxxxxx-xxxxxx-xxxxxxxx"
```

Pass the key on every request using one of:
```
Authorization: Bearer ua-xxxxxxxx-xxxxxx-xxxxxxxx
# or
X-Api-Key: ua-xxxxxxxx-xxxxxx-xxxxxxxx
```

## Providers

Each provider has its own prefix under `/v1/`. Credentials are set via environment variables at server startup.

| Provider | Prefix | Auth (env) |
|---|---|---|
| DeepSeek | `/v1/deepseek` | `DEEPSEEK_COOKIE` + `DEEPSEEK_AUTH_TOKEN` |
| Gemini | `/v1/gemini` | `GEMINI_COOKIE` |
| Grok (xAI) | `/v1/grok` | `GROK_COOKIE` |
| Meta AI | `/v1/metaai` | `META_AI_COOKIE` |
| NotebookLM | `/v1/notebooklm` | `NOTEBOOKLM_STORAGE_PATH` |

## Discover models

```bash
curl $UNOFFICIAL_API_URL/v1/deepseek/models      # deepseek-v3, deepseek-r1, deepseek-v4, deepseek-r4
curl $UNOFFICIAL_API_URL/v1/gemini/models         # gemini-3-flash, gemini-3-pro, gemini-3-flash-thinking, ...
curl $UNOFFICIAL_API_URL/v1/grok/models           # grok-4.20-auto, grok-4.20-fast, grok-4.20-reasoning, ...
curl $UNOFFICIAL_API_URL/v1/metaai/models         # llama-4
curl $UNOFFICIAL_API_URL/v1/notebooklm/models     # notebooklm-2-0
```

All return OpenAI-compatible shape:
```json
{ "object": "list", "data": [
  { "id": "deepseek-v3", "object": "model", "owned_by": "deepseek", "created": 1704067200 },
  { "id": "gemini-3-flash", "object": "model", "owned_by": "gemini", "created": 1704067200 }
]}
```

## Endpoints

| Method | Endpoint | Auth required | Description |
|---|---|---|---|
| `POST` | `/v1/{provider}/chat/completions` | ✅ | Chat completion (OpenAI format) |
| `GET` | `/v1/{provider}/models` | ✅ | List models for provider |
| `GET` | `/health` | ❌ | Health check with provider connection status |
| `GET` | `/` | ❌ | Redirect to API docs (Swagger UI) |
| `POST` | `/v1/keys/generate` | ❌ | Generate a new API key |
| `GET` | `/v1/keys` | ❌ | List all API keys (masked) |
| `POST` | `/v1/keys/revoke` | ❌ | Deactivate an API key |

## Error format

All errors return structured JSON with the correct HTTP status code:

```json
{
  "error": {
    "message": "Description of what went wrong",
    "type": "authentication_error | rate_limit_error | server_error | invalid_request_error",
    "code": "specific_error_code"
  }
}
```

## Capability skills

When the user needs a specific capability, fetch that skill's `SKILL.md` from its raw URL:

| Capability | Raw URL |
|---|---|
| Chat / code-gen | https://raw.githubusercontent.com/2noscript/unofficial-api/refs/heads/master/skills/unofficial-api-chat/SKILL.md |
| Session & Auth Architecture (dev) | https://raw.githubusercontent.com/2noscript/unofficial-api/refs/heads/master/skills/unofficial-api-session-arch/SKILL.md |

## Errors

- `401 missing_api_key` → add `Authorization: Bearer <key>` header
- `401 invalid_api_key` → key is wrong or revoked; generate a new one via `POST /v1/keys/generate`
- `503` → check provider credentials in `.env`
- `400` → check `model` and `messages` fields
- `500` → upstream provider error; check provider status
