from unittest.mock import AsyncMock


def mock_grok_client(app):
    client = AsyncMock()

    async def send_message(message, mode_id=None):
        return "I am Grok, nice to meet you!"

    client.send_message = send_message
    app.state.grok_client = client
    return client


class TestGrok:
    def test_chat_non_stream(self, client, auth_headers, app):
        mock_grok_client(app)

        resp = client.post(
            "/v1/grok/chat/completions",
            json={
                "model": "grok-4.20-auto",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": False,
            },
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "I am Grok" in data["choices"][0]["message"]["content"]

    def test_chat_stream(self, client, auth_headers, app):
        mock_grok_client(app)

        resp = client.post(
            "/v1/grok/chat/completions",
            json={
                "model": "grok-4.20-auto",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": True,
            },
            headers=auth_headers,
        )

        assert resp.status_code == 200
        assert resp.text.startswith("data: ")
        assert "data: [DONE]" in resp.text
        assert "I" in resp.text

    def test_client_unavailable(self, client, auth_headers, app):
        app.state.grok_client = None

        resp = client.post(
            "/v1/grok/chat/completions",
            json={
                "model": "grok-4.20-auto",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": False,
            },
            headers=auth_headers,
        )

        assert resp.status_code == 503

    def test_empty_prompt(self, client, auth_headers, app):
        mock_grok_client(app)

        resp = client.post(
            "/v1/grok/chat/completions",
            json={
                "model": "grok-4.20-auto",
                "messages": [{"role": "user", "content": ""}],
                "stream": False,
            },
            headers=auth_headers,
        )

        assert resp.status_code == 400
