"""Test global session context, cross-session isolation, and auth fallback."""

import os
import uuid
from unittest.mock import patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

os.environ.setdefault("DEEPSEEK_COOKIE", "ds_session_id=test-session")
os.environ.setdefault("DEEPSEEK_AUTH_TOKEN", "test-auth-token")
os.environ.setdefault("NOTEBOOKLM_DEFAULT_NOTEBOOK_ID", "nb-test")

SESSION_STORE: dict[str, dict] = {}


@pytest.fixture
def session_app():
    app = FastAPI()

    @app.middleware("http")
    async def persistent_session_middleware(request: Request, call_next):
        sid = request.headers.get("x-session-id")
        if sid is None:
            request.state.session_data = {}
            request.state.virtual_session_id = uuid.uuid4().hex
        else:
            if sid not in SESSION_STORE:
                SESSION_STORE[sid] = {}
            request.state.session_data = SESSION_STORE[sid]
            request.state.virtual_session_id = sid
        return await call_next(request)

    try:
        from core.routers.deepseek import router as ds_router
    except ImportError:
        ds_router = None

    if ds_router:
        app.include_router(ds_router, prefix="/v1/deepseek")

    return app


@pytest.fixture
def client(session_app):
    SESSION_STORE.clear()
    with TestClient(session_app) as c:
        yield c
    SESSION_STORE.clear()


AUTH = {"Authorization": "Bearer ua-test-test-test"}


class TestCrossSession:
    def test_isolation(self, client):
        with patch("core.routers.deepseek.route.DeepSeekChat") as MockDS:
            instance = MockDS.return_value
            call = [0]
            MISSING_AT = {3, 5}

            def send(prompt, **kw):
                call[0] += 1
                n = call[0]
                instance.chat_session_id = f"ds-{n}"
                instance.parent_message_id = n * 2
                if n in MISSING_AT:
                    return {"ok": False, "content": b'{"code":40300,"msg":"MISSING_HEADER"}'}
                return {"ok": True, "content": {"response": f"ECHO: {prompt}", "thought": ""}}

            instance.send_message.side_effect = send

            client.post("/v1/deepseek/chat/completions", json={
                "model": "deepseek-v3", "stream": False,
                "messages": [{"role": "user", "content": "My name is Alice"}],
            }, headers={**AUTH, "X-Session-Id": "session-a"})

            client.post("/v1/deepseek/chat/completions", json={
                "model": "deepseek-v3", "stream": False,
                "messages": [{"role": "user", "content": "My name is Bob"}],
            }, headers={**AUTH, "X-Session-Id": "session-b"})

            r2a = client.post("/v1/deepseek/chat/completions", json={
                "model": "deepseek-v3", "stream": False,
                "messages": [{"role": "user", "content": "What is my name?"}],
            }, headers={**AUTH, "X-Session-Id": "session-a"})
            assert r2a.status_code == 200, r2a.text
            content_a = r2a.json()["choices"][0]["message"]["content"].lower()
            assert "alice" in content_a

            r2b = client.post("/v1/deepseek/chat/completions", json={
                "model": "deepseek-v3", "stream": False,
                "messages": [{"role": "user", "content": "What is my name?"}],
            }, headers={**AUTH, "X-Session-Id": "session-b"})
            assert r2b.status_code == 200, r2b.text
            content_b = r2b.json()["choices"][0]["message"]["content"].lower()
            assert "bob" in content_b


class TestNoSessionHeader:
    def test_fresh_each_time(self, client):
        """Without X-Session-Id, each request gets a fresh empty session,
        so turn 2 has no context from turn 1."""
        with patch("core.routers.deepseek.route.DeepSeekChat") as MockDS:
            instance = MockDS.return_value
            call = [0]

            def send(prompt, **kw):
                call[0] += 1
                n = call[0]
                if n == 1:
                    instance.chat_session_id = "ds-1"
                    instance.parent_message_id = 2
                    return {"ok": True, "content": {"response": f"ECHO: {prompt}", "thought": ""}}
                return {"ok": True, "content": {"response": f"ECHO: {prompt}", "thought": ""}}

            instance.send_message.side_effect = send

            # Turn 1 — no X-Session-Id, fresh empty session
            r1 = client.post("/v1/deepseek/chat/completions", json={
                "model": "deepseek-v3", "stream": False,
                "messages": [{"role": "user", "content": "Remember: my name is John"}],
            }, headers={**AUTH})
            assert r1.status_code == 200, r1.text

            # Turn 2 — also no X-Session-Id, another fresh session
            r2 = client.post("/v1/deepseek/chat/completions", json={
                "model": "deepseek-v3", "stream": False,
                "messages": [{"role": "user", "content": "What is my name?"}],
            }, headers={**AUTH})
            assert r2.status_code == 200, r2.text

            content = r2.json()["choices"][0]["message"]["content"].lower()
            assert "john" not in content

    def test_disable_auth(self, client, monkeypatch):
        """When DISABLE_AUTH=true, requests without auth headers succeed."""
        monkeypatch.setenv("DISABLE_AUTH", "true")
        with patch("core.routers.deepseek.route.DeepSeekChat") as MockDS:
            instance = MockDS.return_value
            instance.send_message.return_value = {
                "ok": True,
                "content": {"response": "No auth needed", "thought": ""}
            }
            r = client.post("/v1/deepseek/chat/completions", json={
                "model": "deepseek-v3", "stream": False,
                "messages": [{"role": "user", "content": "Hi"}],
            })
            assert r.status_code == 200, r.text
            assert "No auth needed" in r.json()["choices"][0]["message"]["content"]
