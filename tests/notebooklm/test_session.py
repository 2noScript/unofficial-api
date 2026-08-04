from unittest.mock import MagicMock, AsyncMock

AUTH = {"Authorization": "Bearer ua-test-test-test"}
SID = {"X-Session-Id": "sess-nlm-1"}


class TestNotebookLmSession:
    def test_multiturn(self, client):
        mock_client = client.app.state.notebooklm_client
        call = [0]

        async def ask_side(notebook_id=None, question=None, **kw):
            call[0] += 1
            result = MagicMock()
            result.answer = f"ECHO(cid={kw.get('conversation_id','none')}): {question}"
            result.conversation_id = f"nb-cid-{call[0]}"
            result.references = []
            return result

        mock_client.chat.ask = AsyncMock(side_effect=ask_side)

        r1 = client.post("/v1/notebooklm/chat/completions", json={
            "model": "notebooklm-2-0", "stream": False,
            "notebook_id": "nb-test",
            "messages": [{"role": "user", "content": "My name is John"}],
        }, headers={**AUTH, **SID})
        assert r1.status_code == 200, r1.text

        r2 = client.post("/v1/notebooklm/chat/completions", json={
            "model": "notebooklm-2-0", "stream": False,
            "notebook_id": "nb-test",
            "messages": [{"role": "user", "content": "What is my name?"}],
        }, headers={**AUTH, **SID})
        assert r2.status_code == 200, r2.text

        content = r2.json()["choices"][0]["message"]["content"]
        assert "nb-cid-1" in content

    def test_session_error_fallback(self, client):
        mock_client = client.app.state.notebooklm_client
        call = [0]

        async def ask_side(notebook_id=None, question=None, **kw):
            call[0] += 1
            if call[0] == 2:
                raise Exception("session not found")
            result = MagicMock()
            result.answer = f"ECHO(cid={kw.get('conversation_id','none')}): {question}"
            result.conversation_id = f"nb-cid-{call[0]}"
            result.references = []
            return result

        mock_client.chat.ask = AsyncMock(side_effect=ask_side)

        client.post("/v1/notebooklm/chat/completions", json={
            "model": "notebooklm-2-0", "stream": False,
            "notebook_id": "nb-test",
            "messages": [{"role": "user", "content": "My name is John"}],
        }, headers={**AUTH, **SID})

        r2 = client.post("/v1/notebooklm/chat/completions", json={
            "model": "notebooklm-2-0", "stream": False,
            "notebook_id": "nb-test",
            "messages": [{"role": "user", "content": "What is my name?"}],
        }, headers={**AUTH, **SID})
        assert r2.status_code == 200, r2.text

        content = r2.json()["choices"][0]["message"]["content"]
        assert "cid=none" in content
