from unittest.mock import MagicMock


def mock_metaai_client(app):
    client = MagicMock()
    client.prompt.return_value = {"message": "Hello from Llama 4!"}
    app.state.metaai_client = client
    return client


class TestMetaAI:
    def test_chat_non_stream(self, client, auth_headers, app):
        mock_metaai_client(app)

        resp = client.post(
            "/v1/metaai/chat/completions",
            json={
                "model": "llama-4",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": False,
            },
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["choices"][0]["message"]["content"] == "Hello from Llama 4!"
        assert data["model"] == "llama-4"

    def test_chat_stream(self, client, auth_headers, app):
        mock_metaai_client(app)

        resp = client.post(
            "/v1/metaai/chat/completions",
            json={
                "model": "llama-4",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": True,
            },
            headers=auth_headers,
        )

        assert resp.status_code == 200
        assert resp.text.startswith("data: ")
        assert "data: [DONE]" in resp.text

    def test_client_unavailable(self, client, auth_headers, app):
        app.state.metaai_client = None

        resp = client.post(
            "/v1/metaai/chat/completions",
            json={
                "model": "llama-4",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": False,
            },
            headers=auth_headers,
        )

        assert resp.status_code == 503

    def test_empty_prompt(self, client, auth_headers, app):
        mock_metaai_client(app)

        resp = client.post(
            "/v1/metaai/chat/completions",
            json={
                "model": "llama-4",
                "messages": [{"role": "user", "content": ""}],
                "stream": False,
            },
            headers=auth_headers,
        )

        assert resp.status_code == 400
