"""Test multi-turn session context across all providers."""

import os
from unittest.mock import patch, MagicMock, AsyncMock

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
        sid = request.headers.get("x-session-id", "default")
        if sid not in SESSION_STORE:
            SESSION_STORE[sid] = {}
        request.state.session_data = SESSION_STORE[sid]
        request.state.virtual_session_id = sid
        return await call_next(request)

    from core.routers.deepseek import router as ds_router
    from core.routers.gemini import router as gm_router
    from core.routers.grok import router as gk_router
    from core.routers.metaai import router as ma_router
    from core.routers.notebooklm import router as nl_router

    app.include_router(ds_router, prefix="/v1/deepseek")
    app.include_router(gm_router, prefix="/v1/gemini")
    app.include_router(gk_router, prefix="/v1/grok")
    app.include_router(ma_router, prefix="/v1/metaai")
    app.include_router(nl_router, prefix="/v1/notebooklm")

    app.state.gemini_client = MagicMock()
    app.state.notebooklm_client = AsyncMock()
    app.state.metaai_client = MagicMock()
    app.state.grok_client = MagicMock()

    return app


@pytest.fixture
def client(session_app):
    SESSION_STORE.clear()
    with TestClient(session_app) as c:
        yield c
    SESSION_STORE.clear()


AUTH = {"Authorization": "Bearer ua-test-test-test"}
SID = {"X-Session-Id": "sess-1"}


# =====================================================================
# DeepSeek
# =====================================================================


class TestDeepSeekSession:
    def test_multiturn_transcript_fallback(self, client):
        with patch("core.routers.deepseek.route.DeepSeekChat") as MockDS:
            instance = MockDS.return_value
            call = [0]

            def send(prompt, **kw):
                call[0] += 1
                n = call[0]
                if n == 1:
                    instance.chat_session_id = "ds-session-1"
                    instance.parent_message_id = 2
                    return {"ok": True, "content": {"response": f"ECHO: {prompt}", "thought": ""}}
                elif n == 2:
                    return {"ok": False, "content": b'{"code":40300,"msg":"MISSING_HEADER"}'}
                return {"ok": True, "content": {"response": f"ECHO: {prompt}", "thought": ""}}

            instance.send_message.side_effect = send

            r1 = client.post("/v1/deepseek/chat/completions", json={
                "model": "deepseek-v3", "stream": False,
                "messages": [{"role": "user", "content": "Remember: my name is John"}],
            }, headers={**AUTH, **SID})
            assert r1.status_code == 200

            r2 = client.post("/v1/deepseek/chat/completions", json={
                "model": "deepseek-v3", "stream": False,
                "messages": [{"role": "user", "content": "What is my name?"}],
            }, headers={**AUTH, **SID})
            assert r2.status_code == 200

            content = r2.json()["choices"][0]["message"]["content"].lower()
            assert "john" in content

    def test_multiturn_provider_session_chain(self, client):
        with patch("core.routers.deepseek.route.DeepSeekChat") as MockDS:
            instance = MockDS.return_value
            call = [0]

            def send(prompt, **kw):
                call[0] += 1
                nid = call[0] * 2
                instance.chat_session_id = "ds-session-1"
                instance.parent_message_id = nid
                return {"ok": True, "content": {"response": f"ECHO(pid={nid}): {prompt}", "thought": ""}}

            instance.send_message.side_effect = send

            client.post("/v1/deepseek/chat/completions", json={
                "model": "deepseek-v3", "stream": False,
                "messages": [{"role": "user", "content": "Remember: my name is John"}],
            }, headers={**AUTH, **SID})

            r2 = client.post("/v1/deepseek/chat/completions", json={
                "model": "deepseek-v3", "stream": False,
                "messages": [{"role": "user", "content": "What is my name?"}],
            }, headers={**AUTH, **SID})
            assert r2.status_code == 200

            data = SESSION_STORE.get("sess-1", {})
            assert data.get("deepseek_parent_message_id") == 4

    def test_force_virtual_after_fallback(self, client):
        with patch("core.routers.deepseek.route.DeepSeekChat") as MockDS:
            instance = MockDS.return_value
            call_count = [0]

            def send(prompt, **kw):
                call_count[0] += 1
                n = call_count[0]
                if n == 1:
                    instance.chat_session_id = "ds-session-1"
                    instance.parent_message_id = 2
                    return {"ok": True, "content": {"response": "ECHO: turn1", "thought": ""}}
                if n == 2:
                    return {"ok": False, "content": b'{"code":40300,"msg":"MISSING_HEADER"}'}
                instance.chat_session_id = None
                instance.parent_message_id = None
                return {"ok": True, "content": {"response": f"ECHO: {prompt}", "thought": ""}}

            instance.send_message.side_effect = send

            client.post("/v1/deepseek/chat/completions", json={
                "model": "deepseek-v3", "stream": False,
                "messages": [{"role": "user", "content": "Remember: my name is John"}],
            }, headers={**AUTH, **SID})

            client.post("/v1/deepseek/chat/completions", json={
                "model": "deepseek-v3", "stream": False,
                "messages": [{"role": "user", "content": "What is my name?"}],
            }, headers={**AUTH, **SID})

            data = SESSION_STORE.get("sess-1", {})
            assert data.get("deepseek_force_virtual") is True

            client.post("/v1/deepseek/chat/completions", json={
                "model": "deepseek-v3", "stream": False,
                "messages": [{"role": "user", "content": "Check context"}],
            }, headers={**AUTH, **SID})

            data = SESSION_STORE.get("sess-1", {})
            assert data.get("deepseek_chat_session_id") is None
            assert data.get("deepseek_parent_message_id") is None


# =====================================================================
# Gemini
# =====================================================================


class TestGeminiSession:
    def test_multiturn_fallback(self, client):
        with patch("core.routers.gemini.chat.ChatSession") as MockChatSession:
            mock_chat = MockChatSession.return_value
            mock_chat.cid = None
            mock_chat.session_state = None
            mock_chat.metadata = {}

            mock_client = client.app.state.gemini_client
            call = [0]

            class MockOutput:
                def __init__(self, text, thoughts=""):
                    self.text = text
                    self.thoughts = thoughts

            async def gen_side(prompt=None, model=None, chat=None):
                call[0] += 1
                n = call[0]
                if n == 1:
                    chat.cid = "gem-cid"
                    chat.session_state = {"state": "1"}
                    chat.metadata = {"meta": "1"}
                    return MockOutput(text=f"ECHO: {prompt}")
                if n == 2:
                    raise Exception("gemini session error")
                chat.cid = None
                chat.session_state = None
                chat.metadata = {}
                return MockOutput(text=f"ECHO: {prompt}")

            mock_client.generate_content = AsyncMock(side_effect=gen_side)

            r1 = client.post("/v1/gemini/chat/completions", json={
                "model": "gemini-3-flash", "stream": False,
                "messages": [{"role": "user", "content": "Remember: my name is John"}],
            }, headers={**AUTH, **SID})
            assert r1.status_code == 200, r1.text

            r2 = client.post("/v1/gemini/chat/completions", json={
                "model": "gemini-3-flash", "stream": False,
                "messages": [{"role": "user", "content": "What is my name?"}],
            }, headers={**AUTH, **SID})
            assert r2.status_code == 200, r2.text

            content = r2.json()["choices"][0]["message"]["content"].lower()
            assert "john" in content

    def test_provider_session_persists(self, client):
        with patch("core.routers.gemini.chat.ChatSession") as MockChatSession:
            mock_chat = MockChatSession.return_value
            mock_chat.cid = None
            mock_chat.session_state = None
            mock_chat.metadata = {}

            mock_client = client.app.state.gemini_client
            call = [0]

            async def gen_side(prompt=None, model=None, chat=None):
                call[0] += 1
                chat.cid = f"gem-cid-{call[0]}"
                chat.session_state = {"turn": call[0]}
                chat.metadata = {"meta": call[0]}
                return MagicMock(text=f"ECHO: {prompt}", thoughts="")

            mock_client.generate_content = AsyncMock(side_effect=gen_side)

            client.post("/v1/gemini/chat/completions", json={
                "model": "gemini-3-flash", "stream": False,
                "messages": [{"role": "user", "content": "My name is John"}],
            }, headers={**AUTH, **SID})

            r2 = client.post("/v1/gemini/chat/completions", json={
                "model": "gemini-3-flash", "stream": False,
                "messages": [{"role": "user", "content": "What is my name?"}],
            }, headers={**AUTH, **SID})
            assert r2.status_code == 200, r2.text

            data = SESSION_STORE.get("sess-1", {})
            assert data.get("gemini_cid") == "gem-cid-2"
            assert data.get("gemini_session_state") == {"turn": 2}


# =====================================================================
# NotebookLM
# =====================================================================


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


# =====================================================================
# Grok
# =====================================================================


class TestGrokSession:
    def test_multiturn(self, client):
        mock_client = client.app.state.grok_client

        async def send_side(prompt, mode_id=None):
            return f"ECHO: {prompt}"

        mock_client.send_message = AsyncMock(side_effect=send_side)

        r1 = client.post("/v1/grok/chat/completions", json={
            "model": "grok-4.20-auto", "stream": False,
            "messages": [{"role": "user", "content": "Remember: my name is John"}],
        }, headers={**AUTH, **SID})
        assert r1.status_code == 200, r1.text

        r2 = client.post("/v1/grok/chat/completions", json={
            "model": "grok-4.20-auto", "stream": False,
            "messages": [{"role": "user", "content": "What is my name?"}],
        }, headers={**AUTH, **SID})
        assert r2.status_code == 200, r2.text

        content = r2.json()["choices"][0]["message"]["content"].lower()
        assert "john" in content


# =====================================================================
# MetaAI
# =====================================================================


class TestMetaaiSession:
    def test_multiturn(self, client):
        mock_client = client.app.state.metaai_client

        def prompt_side(message=None):
            return {"message": f"ECHO: {message}"}

        mock_client.prompt = MagicMock(side_effect=prompt_side)

        r1 = client.post("/v1/metaai/chat/completions", json={
            "model": "llama-4", "stream": False,
            "messages": [{"role": "user", "content": "Remember: my name is John"}],
        }, headers={**AUTH, **SID})
        assert r1.status_code == 200, r1.text

        r2 = client.post("/v1/metaai/chat/completions", json={
            "model": "llama-4", "stream": False,
            "messages": [{"role": "user", "content": "What is my name?"}],
        }, headers={**AUTH, **SID})
        assert r2.status_code == 200, r2.text

        content = r2.json()["choices"][0]["message"]["content"].lower()
        assert "john" in content


# =====================================================================
# Cross-session isolation
# =====================================================================


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
