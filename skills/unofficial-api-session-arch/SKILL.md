---
name: unofficial-api-session-arch
description: Internal architecture reference for the VirtualSession and API Key system in unofficial-api. Use when modifying session management, adding a new provider adapter, debugging session continuity, or understanding how authentication works at the middleware layer.
---

# Session & Auth Architecture

Internal developer reference for `core/session/`. This covers how sessions are resolved, stored, and per-provider adapters work — not end-user API usage.

## File Map

```
core/session/
├── __init__.py              # exports VirtualSessionStore, VirtualSessionManager, VirtualSessionMiddleware
├── api_key.py               # API key generate / validate / list / revoke (JSON file storage)
├── middleware.py            # FastAPI middleware: auth gate + session resolve + header injection
├── manager.py               # Session ID resolution logic (4-priority algorithm)
├── store.py                 # In-memory session store with TTL + LRU eviction
└── adapters/
    ├── base.py              # BaseSessionAdapter interface
    ├── gemini.py            # Gemini: cid + session_state
    ├── notebooklm.py        # NotebookLM: conversation_id
    ├── deepseek.py          # DeepSeek: chat_session_id
    ├── grok.py              # Grok: (placeholder)
    ├── metaai.py            # Meta AI: (placeholder)
    └── __init__.py          # exports all adapters
```

---

## 1. Middleware Flow (`middleware.py`)

`VirtualSessionMiddleware` runs on every request. Only paths ending in `/chat/completions` are gated.

```
Request
  │
  ├─ not /chat/completions? → pass through
  │
  ├─ extract API key (Authorization: Bearer ... OR X-Api-Key)
  │    └─ missing? → 401 missing_api_key
  │
  ├─ validate_api_key(key)
  │    └─ invalid/revoked? → 401 invalid_api_key
  │
  ├─ read body (cached into request._body so downstream can re-read)
  │
  ├─ manager.resolve(headers, body, provider, api_key_hash, fingerprint)
  │    └─ returns virtual session ID (vid)
  │
  ├─ store.get_or_create(vid) → SessionRecord
  │
  ├─ request.state.virtual_session_id = vid
  ├─ request.state.session_data = record.data   ← routers read/write this
  │
  └─ response.headers['X-Session-Id'] = vid     ← always echoed back
```

Constructor signature:
```python
VirtualSessionMiddleware(
    store,              # VirtualSessionStore instance
    manager,            # VirtualSessionManager instance
    validate_key_fn,    # callable(api_key: str) -> bool
    get_key_hash_fn,    # callable(api_key: str) -> str
    extract_provider_fn # callable(path: str) -> str  e.g. '/v1/gemini/chat/...' → 'gemini'
)
```

---

## 2. Session ID Resolution (`manager.py`)

`VirtualSessionManager.resolve()` — 4-step priority, first match wins:

| Priority | Source | Detail |
|---|---|---|
| **1** | Request headers | Checks `x-session-id`, `session-id`, `session_id`, `x-client-request-id`, `x-conversation-id` |
| **2** | Request body fields | Checks `session_id`, `conversation_id`, `prompt_cache_key` |
| **3** | Assistant history hash | SHA256 of `provider + first-50-chars-of-last-assistant-message`; looks up in `_assistant_cache`; creates new VID if not found |
| **4** | API key hash / fingerprint | Derives a stable VID from `sha256(api_key)[:16]` or `ip:user-agent` |

Key constants:
```python
RESERVED_HEADERS = ['x-session-id', 'session-id', 'session_id', 'x-client-request-id', 'x-conversation-id']
BODY_FIELDS      = ['session_id', 'conversation_id', 'prompt_cache_key']
ASSISTANT_MIN_LEN = 50   # minimum assistant text length to trigger hash lookup
ASSISTANT_CAP_LEN = 50   # characters used for the hash
```

VID format: `uuid4().hex + unix_ms` (no separator), e.g. `a3f8c1d2...1750900000000`.

---

## 3. Session Store (`store.py`)

In-memory, thread-safe. Two separate dicts:

| Dict | Key | Value | Purpose |
|---|---|---|---|
| `_sessions` | vid (str) | `SessionRecord` | Stores per-session provider metadata |
| `_assistant_cache` | sha16 hash (str) | vid (str) | Maps assistant-text-hash → vid for priority-3 resume |

Limits & TTL:
```python
MAX_SESSIONS       = 1000        # LRU evict oldest when full
MAX_ASSISTANT      = 5000        # FIFO evict oldest when full
TTL_MS             = 7_200_000   # 2 hours — sessions expire after last use
CLEANUP_INTERVAL_S = 1800        # background cleanup thread runs every 30 min
```

`SessionRecord` fields:
```python
@dataclass
class SessionRecord:
    session_id:   str
    data:         dict        # arbitrary provider metadata written by adapters
    last_used:    float       # unix timestamp, updated on every access
    api_key_hash: str | None  # for key-based session grouping
```

Key methods:
```python
store.get_or_create(vid, api_key_hash=...) → SessionRecord
store.update(vid, **fields)                # merge fields into record.data
store.get(vid)                             → SessionRecord | None
store.get_sessions_by_api_key(hash)        → list[SessionRecord]
```

---

## 4. Provider Adapters (`adapters/`)

### Interface (`base.py`)

```python
class BaseSessionAdapter:
    @property
    def scope(self) -> str:  # provider name, e.g. 'gemini'
        return ""

    def inject(self, data: dict, request_args: dict) -> dict:
        # Read from session data, return kwargs to merge into provider client call
        return {}

    def extract(self, response, data: dict) -> dict:
        # Read provider response, return updated session data dict
        return data
```

### Existing Adapters

| Adapter | scope | Session key(s) stored | What inject does | What extract does |
|---|---|---|---|---|
| `GeminiAdapter` | `gemini` | `gemini_cid`, `gemini_session_state` | Passes `chat_data={'cid': ...}` and `session_state` to client | Reads `response.cid`, `response.session_state` |
| `NotebookLMAdapter` | `notebooklm` | `notebooklm_conversation_id` | Passes `conversation_id=...` as kwarg | Reads `response.conversation_id` |
| `DeepSeekAdapter` | `deepseek` | `deepseek_chat_session_id` | Sets `chat.chat_session_id` directly on the chat object | Reads `result['_chat_instance'].chat_session_id` |

### How Routers Use Adapters

Pattern used in every integrated router:

```python
from core.session.adapters import get_adapter

# 1. Get session data from middleware
session_data = getattr(request.state, 'session_data', {})
vid = getattr(request.state, 'virtual_session_id', None)

# 2. Get the adapter for this provider
adapter = get_adapter('gemini')   # or 'deepseek', 'notebooklm', etc.

# 3. Build provider client call kwargs
extra_kwargs = adapter.inject(session_data, request_args={'chat': chat_obj})

# 4. Call provider, get response
response = await client.chat(**extra_kwargs)

# 5. Extract new session state from response
new_data = adapter.extract(response, session_data)

# 6. Persist back to store
if vid:
    store.update(vid, **new_data)
```

---

## 5. API Key System (`api_key.py`)

### Key Format

```
ua-{machine_id[:8]}-{key_id}-{crc}
   └──────┬────────┘ └──┬───┘ └──┬─┘
          │             │        └── HMAC-SHA256(secret, machine_id[:8]+key_id)[:8]
          │             └────────── secrets.token_hex(3)  (6 hex chars)
          └──────────────────────── first 8 chars of persistent machine_id
```

### Validation Steps

1. Check prefix == `"ua"`
2. Check key exists in `api_keys.json`
3. Check `is_active == True`
4. If key has 4 parts: verify CRC with `HMAC-SHA256(API_KEY_SECRET, machine_id[:8]+key_id)[:8]`

### Storage

```
~/.unofficial-api/api_keys.json      # default
$UNOFFICIAL_API_DATA_DIR/api_keys.json  # if env var is set
```

File structure:
```json
{
  "machine_id": "a1b2c3d4e5f6a7b8",
  "keys": {
    "ua-a1b2c3d4-ab12cd-ef345678": {
      "name": "production-key",
      "created_at": "2026-06-26T04:00:00",
      "is_active": true
    }
  },
  "last_used": {
    "ua-a1b2c3d4-ab12cd-ef345678": "2026-06-26T04:08:54"
  }
}
```

Env vars:
```bash
API_KEY_SECRET=<secret>               # HMAC secret for CRC, default: 'unofficial-api-key-secret'
UNOFFICIAL_API_DATA_DIR=<path>        # override storage dir, default: ~/.unofficial-api
```

---

## 6. Adding a New Provider Adapter

1. Create `core/session/adapters/{provider}.py`:
```python
from .base import BaseSessionAdapter

class MyProviderAdapter(BaseSessionAdapter):
    @property
    def scope(self) -> str:
        return 'myprovider'   # must match provider prefix in URL

    def inject(self, data: dict, request_args: dict) -> dict:
        kwargs = {}
        sid = data.get('myprovider_session_id')
        if sid:
            kwargs['session_id'] = sid
        return kwargs

    def extract(self, response, data: dict) -> dict:
        new_data = dict(data)
        if hasattr(response, 'session_id') and response.session_id:
            new_data['myprovider_session_id'] = response.session_id
        return new_data
```

2. Register in `core/session/adapters/__init__.py`:
```python
from .myprovider import MyProviderAdapter
```

3. In the router, follow the inject → call → extract → store.update pattern shown in section 4.
