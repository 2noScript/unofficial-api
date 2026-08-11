# Unofficial API Gateway

> **⚠️ Unofficial & Experimental**
>
> This project uses **undocumented, unofficial APIs** from DeepSeek and Google (Gemini). These are **not officially supported** by any provider.
>
> - APIs can break or change without notice
> - Rate limits and throttling apply
> - Credentials (tokens/cookies) expire and must be refreshed
> - **Not affiliated** with DeepSeek or Google
> - For **prototypes, research, and personal projects** only

OpenAI-compatible REST API for **DeepSeek** and **Gemini** with multi-profile dynamic load balancing.

> 📖 [Architecture Overview](docs/ARCHITECTURE.md) — project structure, lifecycle, client types, streaming, auth, Docker
>
> 🔄 [Provider Conversion Details](docs/CONVERSION.md) — OpenAI field mapping per provider
>
> 🔑 [Authentication & Session Management](docs/auth.md) — API key management, Swagger UI setup, conversation context isolation

## Getting Started

1. Pick a provider → create profiles or follow its credential guide
2. Copy and fill `.env`:
   ```bash
   cp .env.example .env
   ```
3. Run the server:
   ```bash
   ./run.sh                  # local
   # or
   docker compose up -d      # Docker
   ```
4. Open Swagger UI: http://localhost:8088/docs
5. Generate an API key (required for chat requests if `DISABLE_AUTH=false`):
   ```bash
   curl -X POST http://localhost:8088/v1/keys/generate \
     -H "Content-Type: application/json" \
     -d '{"name": "my-key"}'
   ```
   Save the returned `api_key` — pass it as `Authorization: Bearer <key>` on every request.

| Provider | Credentials Guide | Specific Endpoints |
|---|---|---|
| DeepSeek | [`docs/deepseek.md`](docs/deepseek.md) | [reasoning_content](docs/deepseek.md#response--additional-fields) |
| Gemini | [`docs/gemini.md`](docs/gemini.md) | [Chats, Gems, Deep Research](docs/gemini.md#provider-specific-endpoints) |

## Profiles & Load Balancing

Credentials are stored and managed via **Profiles** saved in `data/profiles.json` (or configured via API).

- **Multi-Profile Load Balancing**: Chat completion requests automatically load-balance across active profiles (`is_active: true`) using a Round-Robin algorithm.
- **Session-Profile Sticky Affinity**: When passing `X-Session-Id`, the conversation binds to a specific profile to ensure multi-turn context continuity. If the profile becomes inactive, auto-failover seamlessly routes to another active profile.

### Profiles API (`/v1/profiles`)

| Endpoint | Method | Description |
|---|---|---|
| `POST /v1/profiles` | POST | Create a new profile (`deepseek` requires `token`, `gemini` requires `cookie`) |
| `GET /v1/profiles` | GET | List all profiles (optional query parameter `?type=deepseek` or `?type=gemini`) |
| `GET /v1/profiles/{id}` | GET | Get profile details by ID |
| `PUT /v1/profiles/{id}` | PUT | Update profile name, credentials, or `is_active` status |
| `DELETE /v1/profiles/{id}` | DELETE | Delete a profile by ID |

## Configuration

```bash
cp .env.example .env
```

| Env var | Required | Description |
|---|---|---|
| `UNOFFICIAL_API_DATA_DIR` | ❌ | Directory for `profiles.json`, `api_keys.json`, `sessions.json`, `machine_id`. Default: `data` |
| `DISABLE_AUTH` | ❌ | Disable API key authentication in development mode (`true`/`false`). Default: `true` |
| `SESSION_TTL_DAYS` | ❌ | Session lifetime in days after last use. `0` = never expire. Default: `7` |
| `SESSION_MAX_SESSIONS` | ❌ | Max sessions kept in memory. Default: `5000` |
| `API_KEY_SECRET` | ❌ | HMAC secret for API key signing. Change in production. |

## Run

### Docker

```bash
# Run
docker compose up -d
docker compose logs -f
docker compose down
```

### Local

```bash
./run.sh
```

## Common (OpenAI-compatible) Endpoints

These share the same format across all providers.

| Endpoint | Method | DeepSeek | Gemini |
|---|---|---|---|
| `GET /v1/{provider}/models` | GET | ✅ | ✅ |
| `POST /v1/{provider}/chat/completions` | POST | ✅ | ✅ |

### Request body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `model` | string | ✅ | — | Model ID (e.g. `deepseek-v3`, `deepseek-r1`, `gemini-3-flash`, `gemini-3-pro`) |
| `messages` | array | ✅ | — | `[{"role": "user", "content": "..."}]` |
| `stream` | bool | ❌ | `false` | Enable SSE streaming |

### Response

```json
{
  "id": "chatcmpl-1719000000",
  "object": "chat.completion",
  "created": 1719000000,
  "model": "deepseek-v3",
  "choices": [
    {
      "index": 0,
      "message": { "role": "assistant", "content": "..." },
      "finish_reason": "stop"
    }
  ],
  "usage": { "prompt_tokens": 0, "completion_tokens": 42, "total_tokens": 42 }
}
```

Streaming SSE format:
```
data: {"choices": [{"delta": {"content": "..."}}]}
data: [DONE]
```

## System

| Endpoint | Method | Description |
|---|---|---|
| `GET /health` | GET | Provider connection status |
| `GET /` | GET | Redirects to Swagger UI |

## API Key Management

| Endpoint | Method | Description |
|---|---|---|
| `POST /v1/keys/generate` | POST | Generate a new API key |
| `GET /v1/keys` | GET | List all API keys (masked) |
| `POST /v1/keys/revoke` | POST | Deactivate an API key |

See [docs/auth.md](docs/auth.md) for full details.

## Examples

```bash
# DeepSeek
curl -s http://localhost:8088/v1/deepseek/chat/completions \
  -H "Authorization: Bearer <key>" \
  -H "Content-Type: application/json" \
  -d '{"model": "deepseek-v3", "messages": [{"role": "user", "content": "Hi"}]}'

# Gemini
curl -s http://localhost:8088/v1/gemini/chat/completions \
  -H "Authorization: Bearer <key>" \
  -H "Content-Type: application/json" \
  -d '{"model": "gemini-3-flash", "messages": [{"role": "user", "content": "Hi"}]}'

# Session persistence with Sticky Profile Affinity
curl -s http://localhost:8088/v1/gemini/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "X-Session-Id: my-chat-session-001" \
  -H "Content-Type: application/json" \
  -d '{"model": "gemini-3-flash", "messages": [{"role": "user", "content": "What did I just ask?"}]}'
```

