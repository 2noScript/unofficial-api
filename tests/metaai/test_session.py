from unittest.mock import MagicMock

AUTH = {"Authorization": "Bearer ua-test-test-test"}
SID = {"X-Session-Id": "sess-meta-1"}


class TestMetaaiSession:
    def test_multiturn(self, client):
        mock_client = client.app.state.metaai_client

        def prompt_side(message=None):
            return {"message": f"ECHO: {message}"}

        mock_client.prompt = MagicMock(side_effect=prompt_side)

        r1 = client.post("/v1/metaai/chat/completions", json={
            "model": "llama-4", "stream": False,
            "messages": [{"role": "user", "content": "Remember: my name is John"}],
        }, headers={**AUTH, **SID})
        assert r1.status_code == 200, r1.text

        r2 = client.post("/v1/metaai/chat/completions", json={
            "model": "llama-4", "stream": False,
            "messages": [{"role": "user", "content": "What is my name?"}],
        }, headers={**AUTH, **SID})
        assert r2.status_code == 200, r2.text

        content = r2.json()["choices"][0]["message"]["content"].lower()
        assert "john" in content
