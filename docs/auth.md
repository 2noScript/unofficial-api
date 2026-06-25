# Authentication & Session Management

This guide documents the API Key authentication and virtual session management (conversation context isolation) mechanisms built into the Unofficial API Gateway.

---

## 🔑 API Key Authentication

All chat completions endpoints (`/v1/{provider}/chat/completions`) require an API Key to authenticate requests. 

### How to Authenticate
Provide the API Key in your request headers using one of the following methods:

1. **Authorization Header (HTTP Bearer)**:
   ```http
   Authorization: Bearer ua-xxxxxxxx-xxxxxx-xxxxxxxx
   ```

2. **X-Api-Key Header**:
   ```http
   X-Api-Key: ua-xxxxxxxx-xxxxxx-xxxxxxxx
   ```

Requests without a valid API Key or with a deactivated key will receive a `401 Unauthorized` response:
```json
{
  "error": {
    "message": "API key required. Set Authorization: Bearer <key> or X-Api-Key header." or "Invalid or deactivated API key.",
    "type": "auth_error",
    "code": "missing_api_key" or "invalid_api_key"
  }
}
```

---

## ⚙️ Swagger UI Authorization

To test endpoints directly from the Swagger interactive documentation (`http://localhost:8000/docs`):
1. Click the **Authorize** lock button in the top-right corner.
2. Enter your generated API Key under either **HTTPBearer** (e.g., `ua-xxxxxxxx-xxxxxx-xxxxxxxx`) or **APIKeyHeader**.
3. Click **Authorize** and then close the dialog.
4. Any requests sent via "Try it out" will automatically include the authentication header.

---

## 🛠️ API Key Management

The gateway provides endpoints for generating, listing, and revoking API keys. These endpoints do **not** require an API Key to allow bootstrap generation.

### 1. Generate a New API Key
* **Endpoint**: `POST /v1/keys/generate`
* **Request Body**:
  ```json
  {
    "name": "friendly-key-name"
  }
  ```
* **cURL Example**:
  ```bash
  curl -X POST http://localhost:8000/v1/keys/generate \
    -H "Content-Type: application/json" \
    -d '{"name": "production-key"}'
  ```
* **Response**:
  ```json
  {
    "api_key": "ua-740a3193-740296-efa2ec76",
    "name": "production-key"
  }
  ```

### 2. List API Keys
Lists all keys. The keys returned are masked (e.g., `ua-740a3193-740296-e...`) for security.
* **Endpoint**: `GET /v1/keys`
* **cURL Example**:
  ```bash
  curl http://localhost:8000/v1/keys
  ```
* **Response**:
  ```json
  {
    "keys": [
      {
        "key": "ua-740a3193-740296-e...",
        "name": "production-key",
        "created_at": "2026-06-26T04:08:03",
        "is_active": true,
        "last_used": "2026-06-26T04:08:54"
      }
    ]
  }
  ```

### 3. Revoke (Deactivate) an API Key
Deactivates an API key. Once revoked, the key will fail authentication check.
* **Endpoint**: `POST /v1/keys/revoke`
* **Request Body**:
  ```json
  {
    "api_key": "ua-740a3193-740296-efa2ec76"
  }
  ```
* **cURL Example**:
  ```bash
  curl -X POST http://localhost:8000/v1/keys/revoke \
    -H "Content-Type: application/json" \
    -d '{"api_key": "ua-740a3193-740296-efa2ec76"}'
  ```
* **Response**:
  ```json
  {
     "status": "revoked",
     "api_key": "ua-740a3193-740296-efa2ec76"
  }
  ```

### Key Storage
API keys are persistently saved in JSON format.
* **Default Path**: `~/.unofficial-api/api_keys.json`
* **Configuration**: Override the base data directory by setting the `UNOFFICIAL_API_DATA_DIR` environment variable.

---

## 🔄 Session Management (Conversation Context Isolation)

To allow stateless clients to maintain continuous conversations, the gateway implements a virtual session store.

### How it Works
When a request is sent to `/chat/completions`, the gateway resolves a **Session ID** (`X-Session-Id`) using the following priority order:
1. **Request Headers**: Searches for `x-session-id`, `session-id`, `session_id`, `x-client-request-id`, or `x-conversation-id`.
2. **Request Body**: Searches for `session_id`, `conversation_id`, or `prompt_cache_key`.
3. **Assistant History Hashing**: Hashes the first 50 characters of the last `assistant` message in the `messages` array. If this hash matches a cached session, that session is reused.
4. **API Key/IP Fingerprint**: Falls back to deriving a stable session ID from the client's API Key hash or IP/User-Agent fingerprint (creating a new session).

### Continuing a Conversation Context
The session state stores conversation history metadata specific to the provider:
* **Gemini**: Stores the internal `cid` (Chat ID), `rid` (Reply ID), and `rcid` (Reply Candidate ID) under the key `gemini_metadata`.
* **NotebookLM**: Stores the `notebooklm_conversation_id`.
* **DeepSeek**: Stores the `deepseek_chat_session_id`.

#### Step 1: Start a conversation
Send your initial message. The response will contain the `X-Session-Id` header:
```http
HTTP/1.1 200 OK
x-session-id: e5608b0362dc47f4b941e1332515d7801782421723809
...
```

#### Step 2: Continue the conversation
In subsequent requests, pass the returned session ID in the headers to instruct the gateway to resume the same conversation thread:
```bash
curl -X POST http://localhost:8000/v1/gemini/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "X-Session-Id: e5608b0362dc47f4b941e1332515d7801782421723809" \
  -H "Content-Type: application/json" \
  -d '{"model": "gemini-3-flash", "messages": [{"role": "user", "content": "What is my name?"}]}'
```
