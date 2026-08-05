import os
import json
import pytest
from fastapi.testclient import TestClient
from core.server import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer dev-key"}
SID = {"X-Session-Id": "sess-live-chat-test"}


def parse_sse(text: str) -> list[dict]:
    chunks = []
    for line in text.strip().split("\n"):
        if line.startswith("data: ") and line != "data: [DONE]":
            chunks.append(json.loads(line[6:]))
    return chunks


def test_invalid_model():
    """Test API error handling when requesting an unsupported model."""
    print("\n--- [API TEST] Testing Invalid Model Error (HTTP 400) ---")
    resp = client.post(
        "/v1/deepseek/chat/completions",
        json={
            "model": "unsupported-gpt-99",
            "messages": [{"role": "user", "content": "Hi"}],
            "stream": False,
        },
        headers=AUTH,
    )
    print("Invalid Model Response:", resp.status_code, resp.json())
    assert resp.status_code == 400
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "model_not_found"


@pytest.mark.skipif(
    not os.environ.get("DEEPSEEK_AUTH_TOKEN"),
    reason="Live DeepSeek credentials missing in .env",
)
def test_chat_non_stream():
    """Test live non-streaming chat completion with deepseek-v3."""
    print("\n--- [LIVE API TEST] Non-Stream Chat Completion (deepseek-v3) ---")
    resp = client.post(
        "/v1/deepseek/chat/completions",
        json={
            "model": "deepseek-v3",
            "messages": [{"role": "user", "content": "Reply with the single word: OK"}],
            "stream": False,
        },
        headers={**AUTH, **SID},
    )
    assert resp.status_code == 200
    data = resp.json()
    print("Live Non-Stream Response:\n", json.dumps(data, indent=2, ensure_ascii=False))
    assert data["object"] == "chat.completion"
    assert "choices" in data
    assert len(data["choices"]) > 0
    assert data["choices"][0]["message"]["content"] != ""


@pytest.mark.skipif(
    not os.environ.get("DEEPSEEK_AUTH_TOKEN"),
    reason="Live DeepSeek credentials missing in .env",
)
def test_chat_thinking_model():
    """Test live reasoning model with deepseek-r1."""
    print("\n--- [LIVE API TEST] Reasoning Model (deepseek-r1) ---")
    resp = client.post(
        "/v1/deepseek/chat/completions",
        json={
            "model": "deepseek-r1",
            "messages": [{"role": "user", "content": "What is 15 + 27?"}],
            "stream": False,
        },
        headers={**AUTH, **SID},
    )
    assert resp.status_code == 200
    data = resp.json()
    print("Live Thinking Model Response:\n", json.dumps(data, indent=2, ensure_ascii=False))
    assert data["object"] == "chat.completion"
    assert "42" in data["choices"][0]["message"]["content"]


@pytest.mark.skipif(
    not os.environ.get("DEEPSEEK_AUTH_TOKEN"),
    reason="Live DeepSeek credentials missing in .env",
)
def test_chat_stream():
    """Test live SSE streaming chat completion."""
    print("\n--- [LIVE API TEST] Real SSE Streaming (stream: true) ---")
    resp = client.post(
        "/v1/deepseek/chat/completions",
        json={
            "model": "deepseek-v3",
            "messages": [{"role": "user", "content": "Count from 1 to 3"}],
            "stream": True,
        },
        headers={**AUTH, **SID},
    )
    assert resp.status_code == 200
    assert resp.text.startswith("data: ")
    assert "data: [DONE]" in resp.text

    chunks = parse_sse(resp.text)
    print(f"Live Streaming Chunks Received ({len(chunks)} chunks)")

    full = ""
    for c in chunks:
        delta = c.get("choices", [{}])[0].get("delta", {})
        full += delta.get("content", "")
    full = full.rstrip("\n")
    print("Live Stream Full Output:", repr(full))
    assert full != ""
