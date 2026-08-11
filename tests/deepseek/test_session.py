import pytest
from fastapi.testclient import TestClient
from core.server import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer dev-key"}
SID_A = {"X-Session-Id": "sess-real-ds-session-a"}
SID_B = {"X-Session-Id": "sess-real-ds-session-b"}


class TestDeepSeekRealSession:
    def test_multiturn_real_session(self):
        """Test real multi-turn context retention across requests with the same X-Session-Id."""
        # Turn 1: Tell DeepSeek our secret code
        r1 = client.post(
            "/v1/deepseek/chat/completions",
            json={
                "model": "deepseek-v3",
                "messages": [{"role": "user", "content": "My secret code is BETA-77"}],
                "stream": False,
            },
            headers={**AUTH, **SID_A},
        )
        assert r1.status_code == 200, f"Turn 1 failed: {r1.text}"
        data1 = r1.json()
        assert "choices" in data1, f"Invalid response format: {data1}"

        # Turn 2: Ask DeepSeek for the secret code without repeating it in messages
        r2 = client.post(
            "/v1/deepseek/chat/completions",
            json={
                "model": "deepseek-v3",
                "messages": [{"role": "user", "content": "What is my secret code?"}],
                "stream": False,
            },
            headers={**AUTH, **SID_A},
        )
        assert r2.status_code == 200, f"Turn 2 failed: {r2.text}"
        data2 = r2.json()
        content2 = data2["choices"][0]["message"]["content"]

        # Verify live model remembered the secret code BETA-77 across session turns
        assert "BETA-77" in content2 or "beta-77" in content2.lower(), f"Expected BETA-77 in response, got: {content2}"

    def test_session_isolation(self):
        """Test session isolation: Session B must NOT know secret information from Session A."""
        r_b = client.post(
            "/v1/deepseek/chat/completions",
            json={
                "model": "deepseek-v3",
                "messages": [{"role": "user", "content": "What is my secret code?"}],
                "stream": False,
            },
            headers={**AUTH, **SID_B},
        )
        assert r_b.status_code == 200, f"Session B request failed: {r_b.text}"
        data_b = r_b.json()
        content_b = data_b["choices"][0]["message"]["content"]

        # Verify Session B does NOT contain Session A's secret code BETA-77
        assert "BETA-77" not in content_b

    def test_stream_real_session(self):
        """Test real streaming chat completions with X-Session-Id."""
        r = client.post(
            "/v1/deepseek/chat/completions",
            json={
                "model": "deepseek-v3",
                "messages": [{"role": "user", "content": "Say hello in 3 words."}],
                "stream": True,
            },
            headers={**AUTH, **SID_A},
        )
        assert r.status_code == 200, f"Stream request failed: {r.text}"
        assert "data: " in r.text, f"Expected SSE streaming data, got: {r.text}"
