# OpenAI → Provider Conversion Details

This document explains how each provider's native API is mapped to the OpenAI-compatible format.

---

## Model ID Mapping

| OpenAI Convention | DeepSeek | Gemini | NotebookLM | Meta AI | Grok |
|---|---|---|---|---|---|
| `model` field | `deepseek-v3`, `deepseek-r1`, `deepseek-v4`, `deepseek-r4` | `gemini-3-flash`, `gemini-3-pro`, `gemini-3-flash-thinking` | `notebooklm-2-0` | `llama-4` | `grok-3` |

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

| OpenAI Field | DeepSeek | Gemini | NotebookLM | Meta AI | Grok |
|---|---|---|---|---|---|
| `model` | Selects model string | Selects model string | Ignored (always notebooklm-2-0) | Ignored (always llama-4) | Ignored (always grok-3) |
| `messages` | Carried as-is (role `"assistant"` → `"bot"` if needed) | Carried as-is | Last message extracted as `question` | Carried as-is | Carried as-is |
| `stream` | Enables SSE via WebSocket | Enables SSE via `stream=True` | Enables fake line-by-line SSE | Enables SSE via `stream=True` | Enables fake word-by-word SSE |

### Provider-Specific Request Extras

| Provider | Extra Field | Type | Description |
|---|---|---|---|
| Gemini | `files` | `list[str]` | File paths to attach to the message (images, PDFs) |
| NotebookLM | `notebook_id` | `string` | Target notebook ID (required or use `NOTEBOOKLM_DEFAULT_NOTEBOOK_ID` env) |
| NotebookLM | `source_ids` | `list[str]` | Restrict answer to specific source IDs |
| NotebookLM | `conversation_id` | `string` | Continue an existing conversation thread |
| DeepSeek | (none) | — | All params via standard fields |
| Meta AI | (none) | — | All params via standard fields |
| Grok | (none) | — | All params via standard fields |

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

| OpenAI Field | DeepSeek | Gemini | NotebookLM | Meta AI | Grok |
|---|---|---|---|---|---|
| `id` | `"chatcmpl-{timestamp}"` | `"chatcmpl-{timestamp}"` | `"chatcmpl-{timestamp}"` | `"chatcmpl-{timestamp}"` | `"chatcmpl-{timestamp}"` |
| `created` | `int(time.time())` | `int(time.time())` | `int(time.time())` | `int(time.time())` | `int(time.time())` |
| `model` | Request model | Request model | `"notebooklm-2-0"` | `"llama-4"` | `"grok-3"` |
| `choices[].message.content` | SDK response text | SDK response text | `result.answer` | SDK response text | SDK response text |
| `choices[].message.reasoning_content` | Reasoning text (for R1/R4) | Available on thinking models | Not available | Not available | Not available |
| `choices[].finish_reason` | `"stop"` | `"stop"` | `"stop"` | `"stop"` | `"stop"` |
| `usage.prompt_tokens` | 0 (not available) | 0 (not available) | 0 (not available) | 0 (not available) | 0 (not available) |
| `usage.completion_tokens` | Word count (approx) | Word count (approx) | Word count (approx) | Word count (approx) | Word count (approx) |
| `usage.total_tokens` | Word count (approx) | Word count (approx) | Word count (approx) | Word count (approx) | Word count (approx) |

> **Note**: Token counts are approximated by word count. Real token usage would require a tokenizer per provider, which is not implemented.

### NotebookLM Additional Response Fields

NotebookLM's `chat.ask()` returns additional metadata beyond OpenAI format:

| Field | Type | Description |
|---|---|---|
| `notebook_id` | string | Notebook used |
| `conversation_id` | string | Conversation thread ID |
| `turn_number` | int | Turn number in the conversation |
| `is_follow_up` | bool | Whether this is a follow-up question |
| `references` | array | Source citations used in the answer |

---

## Streaming

### Real Streaming (Gemini, DeepSeek, Meta AI)

Data is streamed from the provider as it's generated.

### Fake Streaming (Grok, NotebookLM)

The SDK returns the complete response synchronously. The server then:

**Grok**: Splits the response by spaces, yields each word as a separate SSE event.

**NotebookLM**: Splits the response by newlines, yields each line as a separate SSE event.

### Unified SSE Format

All providers produce the same SSE stream:

```
data: {"choices": [{"delta": {"content": "word"}}]}

data: {"choices": [{"delta": {"content": " "}}]}

data: {"choices": [{"delta": {"content": "next"}}]}

data: [DONE]
```

---

## Provider-Specific Endpoints

These endpoints have no OpenAI equivalent and exist only for their respective providers.

### Gemini

| Path | Mapping |
|---|---|
| `GET /v1/gemini/chats` | `client.get_chats()` |
| `GET /v1/gemini/chats/{cid}` | `client.get_chat_history(cid)` |
| `DELETE /v1/gemini/chats/{cid}` | `client.delete_chat(cid)` |
| `GET /v1/gemini/gems` | `client.list_gems()` |
| `POST /v1/gemini/gems` | `client.create_gem(...)` |
| `PATCH /v1/gemini/gems/{id}` | `client.update_gem(...)` |
| `DELETE /v1/gemini/gems/{id}` | `client.delete_gem(id)` |
| `POST /v1/gemini/research/plan` | `client.create_deep_research_plan(prompt)` |
| `POST /v1/gemini/research/start` | `client.start_deep_research(plan)` |
| `POST /v1/gemini/research/full` | `client.deep_research(prompt)` — one-shot plan→start→wait |
| `GET /v1/gemini/research/{id}/status` | `client.get_deep_research_status(id)` |
| `GET /v1/gemini/chats/{cid}/latest-response` | `client.fetch_latest_chat_response(cid)` |

### NotebookLM

NotebookLM has ~84 endpoints. See [notebooklm.md](notebooklm.md) and [notebooklm-artifacts.md](notebooklm-artifacts.md) for the full breakdown.

### Meta AI

| Path | Mapping |
|---|---|
| `POST /v1/metaai/images/generations` | `client.generate_image_new(prompt, ...)` |
| `POST /v1/metaai/images/upload` | `client.upload_image(file_path)` |
| `POST /v1/metaai/videos/generations` | `client.generate_video_new(prompt, ...)` |
| `POST /v1/metaai/videos/extend` | `client.extend_video(media_id, ...)` |
| `GET /v1/metaai/media/{id}` | `GenerationAPI.fetch_media_by_id(id)` |
| `GET /v1/metaai/media/{id}/status` | `GenerationAPI.fetch_media_status(id)` |

---

## Error Handling Differences

| Scenario | OpenAI | Our Gateway |
|---|---|---|
| Missing auth | 401 `{"error": {...}}` | 503 `{"error": "Provider not initialized"}` |
| Rate limited | 429 | SDK-specific error (varies) |
| Invalid request | 400 | 422 (FastAPI validation) / 400 (manual) |
| Server error | 500 | 500 with SDK error message |

All errors return `{"error": "message"}` regardless of provider.
