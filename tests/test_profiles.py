import pytest
from fastapi.testclient import TestClient
from core.server import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer dev-key"}


from core.profile import delete_profile

class TestProfilesAPI:
    def test_create_deepseek_profile_success(self):
        resp = client.post(
            "/v1/profiles",
            json={
                "type": "deepseek",
                "name": "My DeepSeek Acc",
                "token": "Bearer sample_token_123"
            },
            headers=AUTH
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["type"] == "deepseek"
        assert data["name"] == "My DeepSeek Acc"
        assert data["token"] == "Bearer sample_token_123"
        assert data["cookie"] is None
        assert data["is_active"] is True
        assert data["id"].startswith("prof_deepseek_")
        delete_profile(data["id"])

    def test_create_gemini_profile_success(self):
        resp = client.post(
            "/v1/profiles",
            json={
                "type": "gemini",
                "name": "My Gemini Acc",
                "cookie": "__Secure-1PSID=xyz_cookie"
            },
            headers=AUTH
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["type"] == "gemini"
        assert data["name"] == "My Gemini Acc"
        assert data["cookie"] == "__Secure-1PSID=xyz_cookie"
        assert data["token"] is None
        assert data["id"].startswith("prof_gemini_")
        delete_profile(data["id"])

    def test_create_deepseek_missing_token_fails(self):
        resp = client.post(
            "/v1/profiles",
            json={
                "type": "deepseek",
                "name": "Invalid DeepSeek"
            },
            headers=AUTH
        )
        assert resp.status_code == 400
        assert "token" in resp.json()["detail"].lower()

    def test_create_gemini_missing_cookie_fails(self):
        resp = client.post(
            "/v1/profiles",
            json={
                "type": "gemini",
                "name": "Invalid Gemini"
            },
            headers=AUTH
        )
        assert resp.status_code == 400
        assert "cookie" in resp.json()["detail"].lower()

    def test_list_and_filter_profiles(self):
        # List all
        resp = client.get("/v1/profiles", headers=AUTH)
        assert resp.status_code == 200
        profiles = resp.json()["profiles"]
        assert len(profiles) >= 2

        # Filter deepseek
        resp_ds = client.get("/v1/profiles?type=deepseek", headers=AUTH)
        assert resp_ds.status_code == 200
        ds_profiles = resp_ds.json()["profiles"]
        assert all(p["type"] == "deepseek" for p in ds_profiles)

        # Filter gemini
        resp_gem = client.get("/v1/profiles?type=gemini", headers=AUTH)
        assert resp_gem.status_code == 200
        gem_profiles = resp_gem.json()["profiles"]
        assert all(p["type"] == "gemini" for p in gem_profiles)

    def test_get_profile_by_id(self):
        # Create a profile first
        create_resp = client.post(
            "/v1/profiles",
            json={"type": "deepseek", "name": "Fetch Test", "token": "tok_xyz"},
            headers=AUTH
        )
        pid = create_resp.json()["id"]

        try:
            resp = client.get(f"/v1/profiles/{pid}", headers=AUTH)
            assert resp.status_code == 200
            assert resp.json()["id"] == pid
        finally:
            delete_profile(pid)

    def test_get_nonexistent_profile_404(self):
        resp = client.get("/v1/profiles/prof_nonexistent_9999", headers=AUTH)
        assert resp.status_code == 404

    def test_update_profile(self):
        create_resp = client.post(
            "/v1/profiles",
            json={"type": "deepseek", "name": "Original Name", "token": "old_tok"},
            headers=AUTH
        )
        pid = create_resp.json()["id"]

        try:
            update_resp = client.put(
                f"/v1/profiles/{pid}",
                json={"name": "New Updated Name", "token": "new_tok", "is_active": False},
                headers=AUTH
            )
            assert update_resp.status_code == 200
            data = update_resp.json()
            assert data["name"] == "New Updated Name"
            assert data["token"] == "new_tok"
            assert data["is_active"] is False
        finally:
            delete_profile(pid)

    def test_delete_profile(self):
        create_resp = client.post(
            "/v1/profiles",
            json={"type": "gemini", "name": "Delete Test", "cookie": "cookie_to_delete"},
            headers=AUTH
        )
        pid = create_resp.json()["id"]

        del_resp = client.delete(f"/v1/profiles/{pid}", headers=AUTH)
        assert del_resp.status_code == 200
        assert del_resp.json()["id"] == pid

        # Verify 404 after deletion
        get_resp = client.get(f"/v1/profiles/{pid}", headers=AUTH)
        assert get_resp.status_code == 404

    def test_record_profile_request_and_stats(self):
        from datetime import datetime
        from core.profile import record_profile_request

        create_resp = client.post(
            "/v1/profiles",
            json={"type": "deepseek", "name": "Stats Test", "token": "tok_stats"},
            headers=AUTH
        )
        pid = create_resp.json()["id"]

        try:
            fixed_dt = datetime(2026, 8, 13, 14, 30, 0)
            updated = record_profile_request(pid, timestamp=fixed_dt)
            assert updated is not None
            assert updated["total_requests"] == 1
            assert updated["request_counts"]["2026-08-13"]["14"] == 1

            # Record a second request in the same hour
            record_profile_request(pid, timestamp=fixed_dt)

            # Record a third request in another hour
            another_dt = datetime(2026, 8, 13, 15, 10, 0)
            record_profile_request(pid, timestamp=another_dt)

            # Query API to verify stats
            resp = client.get(f"/v1/profiles/{pid}", headers=AUTH)
            assert resp.status_code == 200
            data = resp.json()
            assert data["total_requests"] == 3
            assert data["request_counts"]["2026-08-13"]["14"] == 2
            assert data["request_counts"]["2026-08-13"]["15"] == 1
        finally:
            delete_profile(pid)

