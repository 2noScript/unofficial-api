class TestHealth:
    def test_health_ok(self, client, auth_headers):
        resp = client.get("/health", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert isinstance(data["gemini_connected"], bool)
        assert isinstance(data["notebooklm_connected"], bool)
        assert isinstance(data["metaai_connected"], bool)
        assert isinstance(data["grok_connected"], bool)

    def test_root_redirects(self, client, auth_headers):
        resp = client.get("/", headers=auth_headers, follow_redirects=False)
        assert resp.status_code in (302, 307)
        assert "/docs" in resp.headers.get("location", "")
