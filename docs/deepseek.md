# DeepSeek

## Credentials

1. Go to https://chat.deepseek.com and sign in
2. Open DevTools (F12) → **Network** tab → reload → click any request to `chat.deepseek.com`
3. Copy the values:

| Source | Env var | Required | How to get |
|---|---|---|---|
| Full `Cookie` header | `DEEPSEEK_COOKIE` | ✅ | DevTools → Network → Request Headers → copy the entire `Cookie: ...` line |
| `authorization` header | `DEEPSEEK_AUTH_TOKEN` | ✅ | DevTools → Network → Request Headers → copy the `authorization: ...` value |

> The `authorization` value looks like `Bearer eyJhbGciOiJIUzI1NiIs...`. Copy the **entire value**. The server auto-prepends `Bearer ` if missing from `DEEPSEEK_AUTH_TOKEN`.

Or use **Cookie-Editor** extension to export all cookies at once.

## Model IDs

| Model | Description |
|---|---|---|
| `deepseek-v3` | Default model without extended thinking |
| `deepseek-r1` | Default model with extended thinking |
| `deepseek-v4` | Default model without extended thinking |
| `deepseek-r4` | Default model with extended thinking |


## Endpoints

DeepSeek has no provider-specific endpoints. Only the [common OpenAI-compatible endpoints](../README.md#common-openai-compatible) (`/models`, `/chat/completions`).

### Chat Completions — Additional fields

Beyond the [common fields](../README.md#common-openai-compatible):

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `search_enabled` | bool | ❌ | `false` | Enable web search with citations (not yet functional in SDK) |

### Response — Additional fields

| Field | Type | Description |
|---|---|---|
| `choices[].message.reasoning_content` | string | Extended thinking trace (for R1/R4 models) |
| `citation` | object | Web search citation data (when search is available) |
| `title` | string | Auto-generated conversation title |

## Examples

```bash
# Basic chat
curl -s http://localhost:8000/v1/deepseek/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-v3",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# Reasoning model (returns reasoning_content)
curl -s http://localhost:8000/v1/deepseek/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-r1",
    "messages": [{"role": "user", "content": "Solve 2+2"}]
  }'

# Expert model
curl -s http://localhost:8000/v1/deepseek/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-v4-expert",
    "messages": [{"role": "user", "content": "Explain quantum computing"}]
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
