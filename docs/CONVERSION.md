# OpenAI → Provider Conversion Details

This document explains how each provider's native API is mapped to the OpenAI-compatible format for **DeepSeek** and **Gemini**.

---

## Model ID Mapping

| OpenAI Convention | DeepSeek | Gemini |
|---|---|---|
| `model` field | `deepseek-v3`, `deepseek-r1` | `gemini-3-flash`, `gemini-3-pro`, `gemini-3-flash-thinking` |

Each provider's `/v1/{provider}/models` endpoint returns its available models.

---

## Chat Completions

### Standard Request Mapping

OpenAI request → each provider's internal format:

```json
{
  "model": "deepseek-v3",
  "messages": [{"role": "user", "content": "Hello!"}],
  "stream": false
}
```

| OpenAI Field | DeepSeek | Gemini |
|---|---|---|
| `model` | Selects model string | Selects model string |
| `messages` | Carried as-is | Carried as-is |
| `stream` | Enables SSE streaming | Enables SSE streaming |

### Provider-Specific Request Extras

| Provider | Extra Field | Type | Description |
|---|---|---|---|
| Gemini | `files` | `list[str]` | File paths to attach to the message (images, PDFs) |
| DeepSeek | (none) | — | All params via standard fields |

### Standard Response Mapping

```json
{
  "id": "chatcmpl-1719000000",
  "object": "chat.completion",
  "created": 1719000000,
  "model": "deepseek-v3",
  "choices": [{"index": 0, "message": {"role": "assistant", "content": "..."}, "finish_reason": "stop"}],
  "usage": {"prompt_tokens": 0, "completion_tokens": 42, "total_tokens": 42}
}
```

| OpenAI Field | DeepSeek | Gemini |
|---|---|---|
| `id` | `"chatcmpl-{timestamp}"` | `"chatcmpl-{timestamp}"` |
| `created` | `int(time.time())` | `int(time.time())` |
| `model` | Request model | Request model |
| `choices[].message.content` | SDK response text | SDK response text |
| `choices[].message.reasoning_content` | Reasoning text (for R1 model) | Available on thinking models |
| `choices[].finish_reason` | `"stop"` | `"stop"` |
| `usage.prompt_tokens` | 0 (not available) | 0 (not available) |
| `usage.completion_tokens` | Word count (approx) | Word count (approx) |
| `usage.total_tokens` | Word count (approx) | Word count (approx) |

> **Note**: Token counts are approximated by word count.

---

## Streaming

Both **DeepSeek** and **Gemini** support real-time SSE streaming. Data is streamed from the provider as it's generated.

### Unified SSE Format

```
data: {"choices": [{"delta": {"content": "word"}}]}

data: {"choices": [{"delta": {"content": " "}}]}

data: {"choices": [{"delta": {"content": "next"}}]}

data: [DONE]
```

---

## Error Handling

| Scenario | OpenAI | Our Gateway |
|---|---|---|
| Missing auth | 401 `{"error": {...}}` | 503 `{"error": "No active profile available"}` |
| Rate limited | 429 | SDK-specific error (varies) |
| Invalid request | 400 | 422 (FastAPI validation) / 400 (manual) |
| Server error | 500 | 500 with error message |

All errors return structured JSON `{"error": {"message": "..."}}`.
