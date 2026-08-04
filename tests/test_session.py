"""Test global session context and cross-session isolation with REAL LIVE API CALLS."""

import os
import pytest
from fastapi.testclient import TestClient
from core.server import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer dev-key"}


@pytest.mark.skipif(
    not os.environ.get("DEEPSEEK_COOKIE") or not os.environ.get("DEEPSEEK_AUTH_TOKEN"),
    reason="Live DeepSeek credentials missing in .env",
)
class TestCrossSession:
    def test_isolation(self):
        """Test live session isolation between session-a and session-b."""
        # Turn 1: session-a sets name Alice
        r1a = client.post(
            "/v1/deepseek/chat/completions",
            json={
                "model": "deepseek-v3",
                "messages": [{"role": "user", "content": "My name is Alice"}],
                "stream": False,
            },
            headers={**AUTH, "X-Session-Id": "sess-live-alice-123"},
        )
        assert r1a.status_code == 200

        # Turn 1: session-b sets name Bob
        r1b = client.post(
            "/v1/deepseek/chat/completions",
            json={
                "model": "deepseek-v3",
                "messages": [{"role": "user", "content": "My name is Bob"}],
                "stream": False,
            },
            headers={**AUTH, "X-Session-Id": "sess-live-bob-456"},
        )
        assert r1b.status_code == 200

        # Turn 2: session-a asks for name -> must answer Alice
        r2a = client.post(
            "/v1/deepseek/chat/completions",
            json={
                "model": "deepseek-v3",
                "messages": [{"role": "user", "content": "What is my name?"}],
                "stream": False,
            },
            headers={**AUTH, "X-Session-Id": "sess-live-alice-123"},
        )
        assert r2a.status_code == 200
        content_a = r2a.json()["choices"][0]["message"]["content"].lower()
        assert "alice" in content_a

        # Turn 2: session-b asks for name -> must answer Bob
        r2b = client.post(
            "/v1/deepseek/chat/completions",
            json={
                "model": "deepseek-v3",
                "messages": [{"role": "user", "content": "What is my name?"}],
                "stream": False,
            },
            headers={**AUTH, "X-Session-Id": "sess-live-bob-456"},
        )
        assert r2b.status_code == 200
        content_b = r2b.json()["choices"][0]["message"]["content"].lower()
        assert "bob" in content_b


@pytest.mark.skipif(
    not os.environ.get("DEEPSEEK_COOKIE") or not os.environ.get("DEEPSEEK_AUTH_TOKEN"),
    reason="Live DeepSeek credentials missing in .env",
)
class TestNoSessionHeader:
    def test_fresh_each_time(self):
        """Without X-Session-Id, each request gets a fresh empty session."""
        r1 = client.post(
            "/v1/deepseek/chat/completions",
            json={
                "model": "deepseek-v3",
                "messages": [{"role": "user", "content": "Remember: my secret code is ZETA-12345"}],
                "stream": False,
            },
            headers={**AUTH},
        )
        assert r1.status_code == 200

        # Turn 2 without X-Session-Id -> fresh session, should NOT know ZETA-12345
        r2 = client.post(
            "/v1/deepseek/chat/completions",
            json={
                "model": "deepseek-v3",
                "messages": [{"role": "user", "content": "What is my secret code?"}],
                "stream": False,
            },
            headers={**AUTH},
        )
        assert r2.status_code == 200
        content = r2.json()["choices"][0]["message"]["content"]
        assert "ZETA-12345" not in content
