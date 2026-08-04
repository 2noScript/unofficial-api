import json
from unittest.mock import patch, MagicMock, AsyncMock


def parse_sse(text: str) -> list[dict]:
    chunks = []
    for line in text.strip().split("\n"):
        if line.startswith("data: ") and line != "data: [DONE]":
            chunks.append(json.loads(line[6:]))
    return chunks


def test_chat_non_stream(client, auth_headers):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1704067200,
        "model": "deepseek-default",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello world!",
                    "reasoning_content": "",
                },
                "finish_reason": "stop",
            }
        ],
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

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


def test_chat_non_stream_with_thinking(client, auth_headers):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1704067200,
        "model": "deepseek-default",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Final answer",
                    "reasoning_content": "Let me think...",
                },
                "finish_reason": "stop",
            }
        ],
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

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


def test_chat_stream(client, auth_headers):
    async def fake_aiter_lines():
        yield 'data: {"id":"chatcmpl-1","choices":[{"delta":{"content":"Hello "}}]}'
        yield 'data: {"id":"chatcmpl-1","choices":[{"delta":{"content":"world!"}}]}'
        yield 'data: [DONE]'

    mock_stream_context = AsyncMock()
    mock_stream_context.__aenter__.return_value.aiter_lines = fake_aiter_lines

    with patch("httpx.AsyncClient.stream", return_value=mock_stream_context):
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
    assert "data: " in resp.text
