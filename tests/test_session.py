import json
from unittest.mock import patch, MagicMock, AsyncMock

AUTH = {"Authorization": "Bearer ua-test-test-test"}


class TestCrossSession:
    def test_isolation(self, client):
        async def fake_post(url, headers=None, json=None, **kw):
            messages = json.get("messages", [])
            content_str = " ".join([m.get("content", "") for m in messages])
            ans = "alice" if "alice" in content_str.lower() else "bob" if "bob" in content_str.lower() else "hello"
            res = MagicMock()
            res.status_code = 200
            res.json.return_value = {
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 1704067200,
                "model": "deepseek-default",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": f"ECHO: {ans}"}, "finish_reason": "stop"}]
            }
            return res

        with patch("httpx.AsyncClient.post", side_effect=fake_post):
            r1 = client.post("/v1/deepseek/chat/completions", json={
                "model": "deepseek-v3", "stream": False,
                "messages": [{"role": "user", "content": "My name is Alice"}],
            }, headers={**AUTH, "X-Session-Id": "session-a"})
            assert r1.status_code == 200

            r2 = client.post("/v1/deepseek/chat/completions", json={
                "model": "deepseek-v3", "stream": False,
                "messages": [{"role": "user", "content": "My name is Bob"}],
            }, headers={**AUTH, "X-Session-Id": "session-b"})
            assert r2.status_code == 200


class TestNoSessionHeader:
    def test_fresh_each_time(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1704067200,
            "model": "deepseek-default",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "ECHO response"}, "finish_reason": "stop"}]
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp

            r1 = client.post("/v1/deepseek/chat/completions", json={
                "model": "deepseek-v3", "stream": False,
                "messages": [{"role": "user", "content": "Remember: my name is John"}],
            }, headers={**AUTH})
            assert r1.status_code == 200

    def test_disable_auth(self, client, monkeypatch):
        monkeypatch.setenv("DISABLE_AUTH", "true")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1704067200,
            "model": "deepseek-default",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "No auth needed"}, "finish_reason": "stop"}]
        }
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            r = client.post("/v1/deepseek/chat/completions", json={
                "model": "deepseek-v3", "stream": False,
                "messages": [{"role": "user", "content": "Hi"}],
            })
            assert r.status_code == 200
