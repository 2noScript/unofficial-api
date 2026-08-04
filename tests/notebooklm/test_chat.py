import os
import json
import pytest
from fastapi.testclient import TestClient
from core.server import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer dev-key"}
SID = {"X-Session-Id": "sess-live-notebooklm-test"}


def parse_sse(text: str) -> list[dict]:
    chunks = []
    for line in text.strip().split("\n"):
        if line.startswith("data: ") and line != "data: [DONE]":
            chunks.append(json.loads(line[6:]))
    return chunks


def test_invalid_model():
    """Test API error handling when requesting an unsupported model."""
    print("\n--- [NOTEBOOKLM API TEST] Testing Invalid Model Error (HTTP 400) ---")
    resp = client.post(
        "/v1/notebooklm/chat/completions",
        json={
            "model": "unsupported-notebooklm-model",
            "messages": [{"role": "user", "content": "Hi"}],
            "stream": False,
        },
        headers=AUTH,
    )
    if resp.status_code == 503:
        pytest.skip("NotebookLM client unauthenticated or storage state missing")
    assert resp.status_code == 400
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "model_not_found"


@pytest.mark.skipif(
    not os.environ.get("NOTEBOOKLM_STORAGE_PATH") or not os.environ.get("NOTEBOOKLM_DEFAULT_NOTEBOOK_ID"),
    reason="Live NotebookLM credentials missing in .env",
)
def test_chat_non_stream():
    """Test live non-streaming chat completion with NotebookLM."""
    print("\n--- [LIVE NOTEBOOKLM TEST] Non-Stream Chat Completion ---")
    resp = client.post(
        "/v1/notebooklm/chat/completions",
        json={
            "model": "notebooklm-default",
            "messages": [{"role": "user", "content": "Summarize notebook"}],
            "stream": False,
        },
        headers={**AUTH, **SID},
    )
    if resp.status_code == 503:
        pytest.skip("NotebookLM client unauthenticated")
    assert resp.status_code == 200
    data = resp.json()
    print("Live NotebookLM Non-Stream Response:\n", json.dumps(data, indent=2, ensure_ascii=False))
    assert data["object"] == "chat.completion"
    assert "choices" in data
    assert len(data["choices"]) > 0
    assert data["choices"][0]["message"]["content"] != ""
