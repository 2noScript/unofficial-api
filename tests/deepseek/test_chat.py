import os
import json
from unittest.mock import patch, MagicMock

os.environ.setdefault("DEEPSEEK_COOKIE", "ds_session_id=test-session")
os.environ.setdefault("DEEPSEEK_AUTH_TOKEN", "test-auth-token")


def parse_sse(text: str) -> list[dict]:
    chunks = []
    for line in text.strip().split("\n"):
        if line.startswith("data: ") and line != "data: [DONE]":
            chunks.append(json.loads(line[6:]))
    return chunks


def test_chat_non_stream(client, auth_headers):
    with patch("core.routers.deepseek.route.DeepSeekChat") as MockDS:
        instance = MockDS.return_value
        instance.send_message.return_value = {
            "ok": True,
            "content": {"response": "Hello world!", "thought": ""},
        }

        resp = client.post(
            "/v1/deepseek/chat/completions",
            json={
                "model": "deepseek-v3",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": False,
            },
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["choices"][0]["message"]["content"] == "Hello world!"
    assert data["choices"][0]["message"]["reasoning_content"] == ""
    assert data["object"] == "chat.completion"


def test_chat_non_stream_with_thinking(client, auth_headers):
    with patch("core.routers.deepseek.route.DeepSeekChat") as MockDS:
        instance = MockDS.return_value
        instance.send_message.return_value = {
            "ok": True,
            "content": {"response": "Final answer", "thought": "Let me think..."},
        }

        resp = client.post(
            "/v1/deepseek/chat/completions",
            json={
                "model": "deepseek-r1",
                "messages": [{"role": "user", "content": "Think step by step"}],
                "stream": False,
            },
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["choices"][0]["message"]["content"] == "Final answer"
    assert data["choices"][0]["message"]["reasoning_content"] == "Let me think..."


def test_chat_non_stream_thinking_disabled_gets_full_text(client, auth_headers):
    with patch("core.routers.deepseek.route.DeepSeekChat") as MockDS:
        instance = MockDS.return_value
        instance.send_message.return_value = {
            "ok": True,
            "content": {"response": "Hello world!", "thought": ""},
        }

        resp = client.post(
            "/v1/deepseek/chat/completions",
            json={
                "model": "deepseek-v3",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": False,
            },
            headers=auth_headers,
        )

    assert resp.json()["choices"][0]["message"]["content"] == "Hello world!"


def test_chat_stream(client, auth_headers):
    with patch("core.routers.deepseek.route.DeepSeekChat") as MockDS:
        instance = MockDS.return_value

        def send_message_side_effect(*args, **kw):
            cb = kw.get("text_callback")
            if cb:
                for chunk in ["Hel", "lo ", "world!"]:
                    cb(chunk)
            return {"ok": True, "content": {"response": "Hello world!", "thought": ""}}

        instance.send_message.side_effect = send_message_side_effect

        resp = client.post(
            "/v1/deepseek/chat/completions",
            json={
                "model": "deepseek-v3",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": True,
            },
            headers=auth_headers,
        )

    assert resp.status_code == 200
    assert resp.text.startswith("data: ")
    assert "data: [DONE]" in resp.text

    chunks = parse_sse(resp.text)
    assert len(chunks) > 0

    full = ""
    for c in chunks:
        delta = c.get("choices", [{}])[0].get("delta", {})
        full += delta.get("content", "")
    full = full.rstrip("\n")
    assert full == "Hello world!"


def test_chat_error_401(client, auth_headers):
    with patch("core.routers.deepseek.route.DeepSeekChat") as MockDS:
        instance = MockDS.return_value
        instance.send_message.return_value = {
            "ok": False,
            "content": "HTTP 401: Unauthorized",
        }

        resp = client.post(
            "/v1/deepseek/chat/completions",
            json={
                "model": "deepseek-v3",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": False,
            },
            headers=auth_headers,
        )

    assert resp.status_code == 401


def test_chat_stream_error(client, auth_headers):
    with patch("core.routers.deepseek.route.DeepSeekChat") as MockDS:
        instance = MockDS.return_value
        instance.send_message.return_value = {
            "ok": False,
            "content": "HTTP 500: Internal Server Error",
        }

        resp = client.post(
            "/v1/deepseek/chat/completions",
            json={
                "model": "deepseek-v3",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": True,
            },
            headers=auth_headers,
        )

    assert resp.status_code == 200
    assert "data: [DONE]" in resp.text
    assert "error" in resp.text or "Internal Server Error" in resp.text


def test_session_error_retry(client, auth_headers):
    with patch("core.routers.deepseek.route.DeepSeekChat") as MockDS:
        instance = MockDS.return_value

        call_count = [0]

        def send_message_side_effect(*args, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                return {
                    "ok": False,
                    "content": "HTTP 404: chat session not found",
                }
            return {
                "ok": True,
                "content": {"response": "Success on retry", "thought": ""},
            }

        instance.send_message.side_effect = send_message_side_effect

        client.post(
            "/v1/deepseek/chat/completions",
            json={
                "model": "deepseek-v3",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": False,
            },
            headers=auth_headers,
        )

    assert call_count[0] == 2
