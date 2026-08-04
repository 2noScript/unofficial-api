import pytest
from fastapi.testclient import TestClient
from core.server import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer dev-key"}


def test_list_models():
    """Test GET /v1/deepseek/models returns available models list according to OpenAI schema."""
    resp = client.get("/v1/deepseek/models", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "list"
    assert "data" in data
    assert isinstance(data["data"], list)
    model_ids = [m["id"] for m in data["data"]]
    assert "deepseek-v3" in model_ids
    assert "deepseek-r1" in model_ids
