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

## Providers

Each provider has its own prefix under `/v1/`. Credentials are set via environment variables at server startup.

| Provider | Prefix | Auth (env) |
|---|---|---|
| DeepSeek | `/v1/deepseek` | `DEEPSEEK_SESSION_ID` + `DEEPSEEK_AUTH_TOKEN` |
| Gemini | `/v1/gemini` | `GEMINI_SECURE_1PSID` + `GEMINI_SECURE_1PSIDTS` |
| Grok (xAI) | `/v1/grok` | `GROK_PROXY_CF_COOKIES` |
| Meta AI | `/v1/metaai` | `META_AI_DATR` + `META_AI_ABRA_SESS` + `META_AI_ECTO_1_SESS` |
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

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/v1/{provider}/chat/completions` | Chat completion (OpenAI format) |
| `GET` | `/v1/{provider}/models` | List models for provider |
| `GET` | `/health` | Health check with provider connection status |
| `GET` | `/` | Redirect to API docs (Swagger UI) |

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

## Errors

- `503` → check provider credentials in `.env`
- `400` → check `model` and `messages` fields
- `500` → upstream provider error; check provider status
