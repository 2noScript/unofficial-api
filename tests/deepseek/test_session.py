import os
import json
import pytest
from fastapi.testclient import TestClient
from core.server import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer dev-key"}
SID_A = {"X-Session-Id": "sess-live-ds-session-a"}
SID_B = {"X-Session-Id": "sess-live-ds-session-b"}


@pytest.mark.skipif(
    not os.environ.get("DEEPSEEK_AUTH_TOKEN"),
    reason="Live DeepSeek credentials missing in .env",
)
class TestDeepSeekLiveSession:
    def test_multiturn_live_session(self):
        """Test multi-turn context retention across requests with the same X-Session-Id."""
        print("\n--- [LIVE SESSION TEST 1] Multi-turn Conversation ---")

        # Turn 1: Tell DeepSeek our secret code
        print("\n[Session A - Turn 1] Sending: 'My secret code is BETA-77'")
        r1 = client.post(
            "/v1/deepseek/chat/completions",
            json={
                "model": "deepseek-v3",
                "messages": [{"role": "user", "content": "My secret code is BETA-77"}],
                "stream": False,
            },
            headers={**AUTH, **SID_A},
        )
        assert r1.status_code == 200
        data1 = r1.json()
        print("Live Response Turn 1:\n", data1["choices"][0]["message"]["content"])

        # Turn 2: Ask DeepSeek for the secret code without repeating it in messages
        print("\n[Session A - Turn 2] Sending: 'What is my secret code?' (only this message)")
        r2 = client.post(
            "/v1/deepseek/chat/completions",
            json={
                "model": "deepseek-v3",
                "messages": [{"role": "user", "content": "What is my secret code?"}],
                "stream": False,
            },
            headers={**AUTH, **SID_A},
        )
        assert r2.status_code == 200
        data2 = r2.json()
        content2 = data2["choices"][0]["message"]["content"]
        print("Live Response Turn 2:\n", content2)

        # Verify live model remembered the secret code BETA-77 across session turns
        assert "BETA-77" in content2 or "beta-77" in content2.lower()

    def test_session_isolation(self):
        """Test session isolation: Session B must NOT know secret information from Session A."""
        print("\n--- [LIVE SESSION TEST 2] Session Isolation ---")

        # Turn 1 in Session B: Ask for the secret code (should not know BETA-77)
        print("\n[Session B - Turn 1] Sending: 'What is my secret code?' (in separate Session B)")
        r_b = client.post(
            "/v1/deepseek/chat/completions",
            json={
                "model": "deepseek-v3",
                "messages": [{"role": "user", "content": "What is my secret code?"}],
                "stream": False,
            },
            headers={**AUTH, **SID_B},
        )
        assert r_b.status_code == 200
        data_b = r_b.json()
        content_b = data_b["choices"][0]["message"]["content"]
        print("Live Session B Response:\n", content_b)

        # Verify Session B does NOT contain Session A's secret code BETA-77
        assert "BETA-77" not in content_b
