from unittest.mock import AsyncMock

AUTH = {"Authorization": "Bearer ua-test-test-test"}
SID = {"X-Session-Id": "sess-grok-1"}


class TestGrokSession:
    def test_multiturn(self, client):
        mock_client = client.app.state.grok_client

        async def send_side(prompt, mode_id=None):
            return f"ECHO: {prompt}"

        mock_client.send_message = AsyncMock(side_effect=send_side)

        r1 = client.post("/v1/grok/chat/completions", json={
            "model": "grok-4.20-auto", "stream": False,
            "messages": [{"role": "user", "content": "Remember: my name is John"}],
        }, headers={**AUTH, **SID})
        assert r1.status_code == 200, r1.text

        r2 = client.post("/v1/grok/chat/completions", json={
            "model": "grok-4.20-auto", "stream": False,
            "messages": [{"role": "user", "content": "What is my name?"}],
        }, headers={**AUTH, **SID})
        assert r2.status_code == 200, r2.text

        content = r2.json()["choices"][0]["message"]["content"].lower()
        assert "john" in content
