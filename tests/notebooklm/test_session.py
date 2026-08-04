import os
import json
import pytest
from fastapi.testclient import TestClient
from core.server import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer dev-key"}
SID = {"X-Session-Id": "sess-live-notebooklm-session"}


@pytest.mark.skipif(
    not os.environ.get("NOTEBOOKLM_STORAGE_PATH") or not os.environ.get("NOTEBOOKLM_DEFAULT_NOTEBOOK_ID"),
    reason="Live NotebookLM credentials missing in .env",
)
class TestNotebookLmSession:
    def test_multiturn(self):
        print("\n--- [LIVE NOTEBOOKLM TEST] Multi-turn Conversation ---")
        r1 = client.post(
            "/v1/notebooklm/chat/completions",
            json={
                "model": "notebooklm-default",
                "messages": [{"role": "user", "content": "Hello NotebookLM"}],
                "stream": False,
            },
            headers={**AUTH, **SID},
        )
        if r1.status_code == 503:
            pytest.skip("NotebookLM client unauthenticated")
        assert r1.status_code == 200
        data1 = r1.json()
        print("NotebookLM Turn 1 Response:\n", json.dumps(data1, indent=2, ensure_ascii=False))

        r2 = client.post(
            "/v1/notebooklm/chat/completions",
            json={
                "model": "notebooklm-default",
                "messages": [{"role": "user", "content": "What did I ask previously?"}],
                "stream": False,
            },
            headers={**AUTH, **SID},
        )
        assert r2.status_code == 200
        data2 = r2.json()
        print("NotebookLM Turn 2 Response:\n", json.dumps(data2, indent=2, ensure_ascii=False))
        assert data2["choices"][0]["message"]["content"] != ""
