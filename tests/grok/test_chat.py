import os
import json
import pytest
from fastapi.testclient import TestClient
from core.server import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer dev-key"}
SID = {"X-Session-Id": "sess-live-grok-test"}


def parse_sse(text: str) -> list[dict]:
    chunks = []
    for line in text.strip().split("\n"):
        if line.startswith("data: ") and line != "data: [DONE]":
            chunks.append(json.loads(line[6:]))
    return chunks


def test_invalid_model():
    """Test API error handling when requesting an unsupported model."""
    print("\n--- [GROK API TEST] Testing Invalid Model Error (HTTP 400) ---")
    resp = client.post(
        "/v1/grok/chat/completions",
        json={
            "model": "unsupported-grok-model",
            "messages": [{"role": "user", "content": "Hi"}],
            "stream": False,
        },
        headers=AUTH,
    )
    if resp.status_code == 503:
        pytest.skip("Grok client unauthenticated or cookie missing in .env")
    assert resp.status_code == 400
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "model_not_found"


@pytest.mark.skipif(
    not os.environ.get("GROK_COOKIE"),
    reason="Live Grok credentials missing in .env",
)
def test_chat_non_stream():
    """Test live non-streaming chat completion with Grok."""
    print("\n--- [LIVE GROK TEST] Non-Stream Chat Completion ---")
    resp = client.post(
        "/v1/grok/chat/completions",
        json={
            "model": "grok-3",
            "messages": [{"role": "user", "content": "Reply with 'Hello'"}],
            "stream": False,
        },
        headers={**AUTH, **SID},
    )
    assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text}"
    data = resp.json()
    print("Live Grok Non-Stream Response:\n", json.dumps(data, indent=2, ensure_ascii=False))
    assert data["object"] == "chat.completion"
    assert "choices" in data
    assert len(data["choices"]) > 0
    assert data["choices"][0]["message"]["content"] != ""


@pytest.mark.skipif(
    not os.environ.get("GROK_COOKIE"),
    reason="Live Grok credentials missing in .env",
)
def test_chat_stream():
    """Test live SSE streaming chat completion with Grok."""
    print("\n--- [LIVE GROK TEST] Real SSE Streaming (stream: true) ---")
    resp = client.post(
        "/v1/grok/chat/completions",
        json={
            "model": "grok-3",
            "messages": [{"role": "user", "content": "Count 1 2 3"}],
            "stream": True,
        },
        headers={**AUTH, **SID},
    )
    assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text}"
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
