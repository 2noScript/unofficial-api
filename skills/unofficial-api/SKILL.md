---
name: unofficial-api
description: Entry point for Unofficial API — OpenAI-compatible REST gateway for DeepSeek and Gemini. Use when the user mentions Unofficial API, UNOFFICIAL_API_URL, or wants AI without writing provider boilerplate. This skill covers setup + indexes capability skills; fetch the relevant capability SKILL.md from the URLs below when needed.
---

# Unofficial API

OpenAI-compatible REST gateway aggregating DeepSeek and Gemini into a single endpoint with multi-profile load balancing. One URL, many models.

## Setup

```bash
export UNOFFICIAL_API_URL="http://localhost:8088"      # local or deployed URL
```

All requests: `${UNOFFICIAL_API_URL}/v1/{provider}/chat/completions`.

Verify: `curl $UNOFFICIAL_API_URL/health` → `{"status":"ok"}`.

## Authentication

Chat endpoints require an API key if authentication is enabled (`DISABLE_AUTH=false`). Generate one first:

```bash
curl -X POST $UNOFFICIAL_API_URL/v1/keys/generate \
  -H "Content-Type: application/json" \
  -d '{"name": "my-key"}'

export UNOFFICIAL_API_KEY="sk-xxxxxxxx-xxxx-xxxx"
```

Pass the key on every request:
```
Authorization: Bearer sk-xxxxxxxx-xxxx-xxxx
```

## Profiles & Multi-Account Load Balancing

Profiles are managed via `/v1/profiles` and stored in `data/profiles.json`. Chat completions automatically load-balance across active profiles (`is_active: true`) using Round-Robin, with sticky session affinity when using `X-Session-Id`.

| Provider | Prefix | Credential Field |
|---|---|---|
| DeepSeek | `/v1/deepseek` | `token` |
| Gemini | `/v1/gemini` | `cookie` |

## Discover models

```bash
curl $UNOFFICIAL_API_URL/v1/deepseek/models      # deepseek-v3, deepseek-r1
curl $UNOFFICIAL_API_URL/v1/gemini/models        # gemini-3-flash, gemini-3-pro, ...
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
| `POST` | `/v1/profiles` | ❌ | Create a new profile |
| `GET` | `/v1/profiles` | ❌ | List profiles |
| `GET` | `/health` | ❌ | Health check |
| `GET` | `/` | ❌ | Redirect to API docs (Swagger UI) |
| `POST` | `/v1/keys/generate` | ❌ | Generate a new API key |
| `GET` | `/v1/keys` | ❌ | List all API keys |
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
- `503` → check active profiles via `GET /v1/profiles`
- `400` → check `model` and `messages` fields
- `500` → upstream provider error; check provider status

