---
name: unofficial-api-chat
description: Chat / code generation via Unofficial API using OpenAI /v1/chat/completions format with streaming support across DeepSeek, Gemini, Grok (xAI), Meta AI (Llama 4), and NotebookLM. Use when the user wants to ask an LLM, generate code, summarize text, or run prompts through Unofficial API.
---

# Unofficial API — Chat

Requires `UNOFFICIAL_API_URL`. See https://raw.githubusercontent.com/2noscript/unofficial-api/refs/heads/master/skills/unofficial-api/SKILL.md for setup and provider credentials.

## Endpoints

`POST $UNOFFICIAL_API_URL/v1/{provider}/chat/completions`

| Provider | URL |
|---|---|
| DeepSeek | `/v1/deepseek/chat/completions` |
| Gemini | `/v1/gemini/chat/completions` |
| Grok | `/v1/grok/chat/completions` |
| Meta AI | `/v1/metaai/chat/completions` |
| NotebookLM | `/v1/notebooklm/chat/completions` |

## Discover

```bash
curl $UNOFFICIAL_API_URL/v1/deepseek/models | jq '.data[].id'
curl $UNOFFICIAL_API_URL/v1/gemini/models  | jq '.data[].id'
curl $UNOFFICIAL_API_URL/v1/grok/models    | jq '.data[].id'
curl $UNOFFICIAL_API_URL/v1/metaai/models  | jq '.data[].id'
curl $UNOFFICIAL_API_URL/v1/notebooklm/models | jq '.data[].id'
```

## Request format

OpenAI-compatible chat completions format:

| Field | Required | Type | Notes |
|---|---|---|---|
| `model` | yes | string | from `/v1/{provider}/models` |
| `messages` | yes | array | `[{role, content}]` |
| `stream` | no | boolean | default `false` |

`content` can be a string or an array of parts: `[{"type":"text","text":"..."}]`.

## Response shape

### Non-streaming (`stream: false`)

```json
{
  "id": "chatcmpl-1740000000",
  "object": "chat.completion",
  "created": 1740000000,
  "model": "deepseek-v3",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?",
        "reasoning_content": null
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 0,
    "completion_tokens": 8,
    "total_tokens": 8
  }
}
```

NotebookLM adds provider-specific fields: `notebook_id`, `conversation_id`, `references[]`.

DeepSeek returns `reasoning_content` for R1/R4 models.

### Streaming (`stream: true`)

SSE stream — each chunk is a `data:` line followed by `\n\n`. Ends with `data: [DONE]\n\n`.

```
data: {"id":"chatcmpl-1740000000","object":"chat.completion.chunk","created":1740000000,"model":"deepseek-v3","choices":[{"index":0,"delta":{"role":"assistant","content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-1740000000","object":"chat.completion.chunk","created":1740000000,"model":"deepseek-v3","choices":[{"index":0,"delta":{"content":"!"},"finish_reason":null}]}

data: {"id":"chatcmpl-1740000000","object":"chat.completion.chunk","created":1740000000,"model":"deepseek-v3","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

First chunk: `delta` includes `role: "assistant"`. Last chunk: `finish_reason: "stop"`.

### Error

```json
{
  "error": {
    "message": "HTTP 401: Unauthorized",
    "type": "authentication_error",
    "code": "invalid_credentials"
  }
}
```

In streaming, errors appear as SSE:
```
data: {"error":{"message":"...","type":"authentication_error","code":"invalid_credentials"}}

data: [DONE]
```

## Examples

### DeepSeek (non-streaming)

```bash
curl -X POST $UNOFFICIAL_API_URL/v1/deepseek/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v3","messages":[{"role":"user","content":"Write a Python function to sort a list"}],"stream":false}'
```

### Gemini (streaming)

```bash
curl -X POST $UNOFFICIAL_API_URL/v1/gemini/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gemini-3-flash","messages":[{"role":"user","content":"Explain quantum computing"}],"stream":true}'
```

### Grok

```bash
curl -X POST $UNOFFICIAL_API_URL/v1/grok/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"grok-4.20-auto","messages":[{"role":"user","content":"What is the meaning of life?"}],"stream":false}'
```

### Meta AI (Llama 4)

```bash
curl -X POST $UNOFFICIAL_API_URL/v1/metaai/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"llama-4","messages":[{"role":"user","content":"Write a poem about AI"}],"stream":false}'
```

### NotebookLM (source-grounded Q&A)

```bash
curl -X POST $UNOFFICIAL_API_URL/v1/notebooklm/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"notebooklm-2-0","messages":[{"role":"user","content":"Summarize the key points from my sources"}],"stream":false}'
```

### Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1/deepseek",
    api_key="not-needed"  # auth via env vars on server
)

response = client.chat.completions.create(
    model="deepseek-v3",
    messages=[{"role": "user", "content": "Hello!"}],
    stream=True,
)

for chunk in response:
    print(chunk.choices[0].delta.content or "", end="")
```

## Models per provider

### DeepSeek

| Model | Thinking |
|---|---|
| `deepseek-v3` | No |
| `deepseek-r1` | Yes |
| `deepseek-v4` | No |
| `deepseek-r4` | Yes |

### Gemini

| Model |
|---|
| `gemini-3-flash` |
| `gemini-3-pro` |
| `gemini-3-flash-thinking` |
| `gemini-3-flash-lite` |
| (and more — use `/v1/gemini/models` to list) |

### Grok

| Model |
|---|
| `grok-4.20-auto` |
| `grok-4.20-fast` |
| `grok-4.20-reasoning` |
| `grok-4.3-beta` |
| (and more — use `/v1/grok/models` to list) |

### Meta AI

| Model |
|---|
| `llama-4` |

### NotebookLM

| Model |
|---|
| `notebooklm-2-0` |

## Provider notes

| Provider | Real streaming | Reasoning content | Image support |
|---|---|---|---|
| DeepSeek | No (fake — full response then split) | Yes (R1/R4) | No |
| Gemini | Yes (true async stream) | No (via thoughts) | No |
| Grok | No (fake — full response then split) | No | No |
| Meta AI | Yes (via ThreadPool) | No | No |
| NotebookLM | No (fake — full response then split) | No | No |
