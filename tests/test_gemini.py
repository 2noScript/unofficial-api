from unittest.mock import MagicMock, AsyncMock


async def _generate_content(**kw):
    return MagicMock(text="Hello Gemini!", thoughts="")


async def _generate_content_stream(**kw):
    for t in ["Hel", "lo ", "Gemini!"]:
        yield MagicMock(text_delta=t)


def mock_gemini_client(app):
    client = AsyncMock()
    client.generate_content = _generate_content
    client.generate_content_stream = _generate_content_stream
    app.state.gemini_client = client
    return client


class TestGemini:
    def test_chat_non_stream(self, client, auth_headers, app):
        mock_gemini_client(app)

        resp = client.post(
            "/v1/gemini/chat/completions",
            json={
                "model": "gemini-3-flash",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": False,
            },
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["choices"][0]["message"]["content"] == "Hello Gemini!"

    def test_chat_stream(self, client, auth_headers, app):
        mock_gemini_client(app)

        resp = client.post(
            "/v1/gemini/chat/completions",
            json={
                "model": "gemini-3-flash",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": True,
            },
            headers=auth_headers,
        )

        assert resp.status_code == 200
        assert resp.text.startswith("data: ")
        assert "data: [DONE]" in resp.text
        assert "content\": \"Hel" in resp.text
        assert "content\": \"lo " in resp.text
        assert "content\": \"Gemini!" in resp.text

    def test_client_unavailable(self, client, auth_headers, app):
        app.state.gemini_client = None

        resp = client.post(
            "/v1/gemini/chat/completions",
            json={
                "model": "gemini-3-flash",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": False,
            },
            headers=auth_headers,
        )

        assert resp.status_code == 503
        assert "not initialized" in resp.text.lower()
