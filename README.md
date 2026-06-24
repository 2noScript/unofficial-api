# Unofficial API Gateway

OpenAI-compatible API cho DeepSeek và Gemini.

## Cách lấy credentials

### DeepSeek

1. Vào https://chat.deepseek.com, đăng nhập
2. Mở DevTools (F12) → **Application** → **Cookies** → `https://chat.deepseek.com`
3. Copy các giá trị:

| Cookie | Env var |
|--------|---------|
| `ds_session_id` | `DEEPSEEK_SESSION_ID` |
| `authorization` | `DEEPSEEK_AUTH_TOKEN` |

Hoặc dùng extension **Cookie-Editor** để export toàn bộ cookies.

---

### Gemini (Google)

1. Vào https://gemini.google.com, đăng nhập
2. Mở DevTools (F12) → **Application** → **Cookies** → `https://gemini.google.com`
3. Copy các giá trị:

| Cookie | Env var | Bắt buộc |
|--------|---------|----------|
| `__Secure-1PSID` | `GEMINI_SECURE_1PSID` | ✅ |
| `__Secure-1PSIDTS` | `GEMINI_SECURE_1PSIDTS` | ❌ (tùy tài khoản) |

> **Lưu ý**: Cookies có thời hạn. Nếu hết hạn, làm lại các bước trên để lấy cookie mới.

---

## Cấu hình

```bash
cp .env.example .env
```

Sửa file `.env`:

```env
DEEPSEEK_SESSION_ID=nhập_session_id_vào_đây
DEEPSEEK_AUTH_TOKEN=nhập_auth_token_vào_đây
GEMINI_SECURE_1PSID=nhập_secure_1psid_vào_đây
GEMINI_SECURE_1PSIDTS=nhập_secure_1psidts_vào_đây
```

## Docker

### Build & push đa nền tảng

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t 2noscript/unofficial-api:latest \
  --push .
```

### Chạy bằng docker-compose

```bash
docker compose up -d
```

Xem log:
```bash
docker compose logs -f
```

Dừng:
```bash
docker compose down
```

## Chạy (local)

```bash
./run.sh
```

Mở Swagger UI: http://localhost:8000/docs

## Endpoints

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/v1/deepseek/models` | GET | Danh sách DeepSeek models |
| `/v1/deepseek/chat/completions` | POST | Chat với DeepSeek |
| `/v1/gemini/models` | GET | Danh sách Gemini models |
| `/v1/gemini/chat/completions` | POST | Chat với Gemini |
| `/health` | GET | Kiểm tra server |
