import os
import pytest

AUTH = {"Authorization": "Bearer dev-key"}
SID = {"X-Session-Id": "sess-grok-live-multiturn"}


class TestGrokSession:
    @pytest.mark.skipif(
        not os.environ.get("GROK_COOKIE"),
        reason="Live Grok credentials missing in .env",
    )
    def test_multiturn(self, client):
        """Test real multi-turn conversation with Grok over WebSocket Gateway."""
        print("\n--- [LIVE GROK TEST] Multi-turn Conversation ---")

        # Turn 1: Provide information
        r1 = client.post(
            "/v1/grok/chat/completions",
            json={
                "model": "grok-3",
                "stream": False,
                "messages": [{"role": "user", "content": "Remember: my favorite color is neon blue."}],
            },
            headers={**AUTH, **SID},
        )
        assert r1.status_code == 200, f"HTTP {r1.status_code}: {r1.text}"
        ans1 = r1.json()["choices"][0]["message"]["content"]
        print("Turn 1 Answer:", repr(ans1))
        assert ans1 != ""

        # Turn 2: Query information from memory using same X-Session-Id
        r2 = client.post(
            "/v1/grok/chat/completions",
            json={
                "model": "grok-3",
                "stream": False,
                "messages": [{"role": "user", "content": "What is my favorite color?"}],
            },
            headers={**AUTH, **SID},
        )
        assert r2.status_code == 200, f"HTTP {r2.status_code}: {r2.text}"
        ans2 = r2.json()["choices"][0]["message"]["content"].lower()
        print("Turn 2 Answer:", repr(ans2))
        assert "blue" in ans2 or "neon" in ans2

