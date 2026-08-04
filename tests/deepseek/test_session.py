import json
from unittest.mock import patch, MagicMock, AsyncMock

AUTH = {"Authorization": "Bearer ua-test-test-test"}
SID = {"X-Session-Id": "sess-ds-1"}


class TestDeepSeekSession:
    def test_multiturn_proxy(self, client):
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
                        "content": "Hello John!",
                        "reasoning_content": "",
                    },
                    "finish_reason": "stop",
                }
            ],
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp

            r1 = client.post("/v1/deepseek/chat/completions", json={
                "model": "deepseek-v3", "stream": False,
                "messages": [{"role": "user", "content": "Remember: my name is John"}],
            }, headers={**AUTH, **SID})
            assert r1.status_code == 200

            r2 = client.post("/v1/deepseek/chat/completions", json={
                "model": "deepseek-v3", "stream": False,
                "messages": [{"role": "user", "content": "What is my name?"}],
            }, headers={**AUTH, **SID})
            assert r2.status_code == 200
            assert "john" in r2.json()["choices"][0]["message"]["content"].lower()
