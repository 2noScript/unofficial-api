import os
from unittest.mock import MagicMock, AsyncMock


class FakeResult:
    def __init__(self, answer="Summary answer", conversation_id="conv-1", turn_number=1, is_follow_up=False, references=None):
        self.answer = answer
        self.conversation_id = conversation_id
        self.turn_number = turn_number
        self.is_follow_up = is_follow_up
        self.references = references or []


def mock_notebooklm_client(app):
    client = AsyncMock()

    async def ask(notebook_id, question, **kw):
        return FakeResult(
            answer="Here is the summary of your sources.",
            conversation_id="conv-abc",
            turn_number=1,
            is_follow_up=False,
            references=[],
        )

    client.chat = AsyncMock()
    client.chat.ask = ask
    app.state.notebooklm_client = client
    return client


class TestNotebookLM:
    def test_chat_non_stream(self, client, auth_headers, app, monkeypatch):
        mock_notebooklm_client(app)
        monkeypatch.setenv("NOTEBOOKLM_DEFAULT_NOTEBOOK_ID", "nb-123")

        resp = client.post(
            "/v1/notebooklm/chat/completions",
            json={
                "model": "notebooklm-2-0",
                "messages": [{"role": "user", "content": "Summarize sources"}],
                "stream": False,
            },
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data["choices"][0]["message"]["content"].lower()
        assert data["conversation_id"] == "conv-abc"
        assert data["turn_number"] == 1
        assert data["is_follow_up"] is False

    def test_chat_stream(self, client, auth_headers, app, monkeypatch):
        mock_notebooklm_client(app)
        monkeypatch.setenv("NOTEBOOKLM_DEFAULT_NOTEBOOK_ID", "nb-123")

        resp = client.post(
            "/v1/notebooklm/chat/completions",
            json={
                "model": "notebooklm-2-0",
                "messages": [{"role": "user", "content": "Summarize"}],
                "stream": True,
            },
            headers=auth_headers,
        )

        assert resp.status_code == 200
        assert resp.text.startswith("data: ")
        assert "data: [DONE]" in resp.text

    def test_missing_notebook_id(self, client, auth_headers, app, monkeypatch):
        mock_notebooklm_client(app)
        monkeypatch.delenv("NOTEBOOKLM_DEFAULT_NOTEBOOK_ID", raising=False)

        resp = client.post(
            "/v1/notebooklm/chat/completions",
            json={
                "model": "notebooklm-2-0",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": False,
            },
            headers=auth_headers,
        )

        assert resp.status_code == 400
        assert "NOTEBOOKLM_DEFAULT_NOTEBOOK_ID" in resp.text
