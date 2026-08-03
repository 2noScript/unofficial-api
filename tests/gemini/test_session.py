import uuid
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

AUTH = {"Authorization": "Bearer ua-test-key"}
SID = {"x-session-id": "sess-gemini-1"}
SESSION_STORE = {}


@pytest.fixture
def gemini_session_app():
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

    from core.routers.gemini import router as gm_router
    app.include_router(gm_router, prefix="/v1/gemini")

    app.state.gemini_client = MagicMock()
    return app


@pytest.fixture
def gemini_client(gemini_session_app):
    SESSION_STORE.clear()
    with TestClient(gemini_session_app) as c:
        yield c


class TestGeminiSession:
    def test_multiturn_fallback(self, gemini_client):
        with patch("core.routers.gemini.chat.ChatSession") as MockChatSession:
            mock_chat = MockChatSession.return_value
            mock_chat.cid = None
            mock_chat.session_state = None
            mock_chat.metadata = {}

            mock_client = gemini_client.app.state.gemini_client
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

            r1 = gemini_client.post("/v1/gemini/chat/completions", json={
                "model": "gemini-3-flash", "stream": False,
                "messages": [{"role": "user", "content": "Remember: my name is John"}],
            }, headers={**AUTH, **SID})
            assert r1.status_code == 200, r1.text

            r2 = gemini_client.post("/v1/gemini/chat/completions", json={
                "model": "gemini-3-flash", "stream": False,
                "messages": [{"role": "user", "content": "What is my name?"}],
            }, headers={**AUTH, **SID})
            assert r2.status_code == 200, r2.text

            content = r2.json()["choices"][0]["message"]["content"].lower()
            assert "john" in content

    def test_provider_session_persists(self, gemini_client):
        with patch("core.routers.gemini.chat.ChatSession") as MockChatSession:
            mock_chat = MockChatSession.return_value
            mock_chat.cid = None
            mock_chat.session_state = None
            mock_chat.metadata = {}

            mock_client = gemini_client.app.state.gemini_client
            call = [0]

            async def gen_side(prompt=None, model=None, chat=None):
                call[0] += 1
                chat.cid = f"gem-cid-{call[0]}"
                chat.session_state = {"turn": call[0]}
                chat.metadata = {"meta": call[0]}
                return MagicMock(text=f"ECHO: {prompt}", thoughts="")

            mock_client.generate_content = AsyncMock(side_effect=gen_side)

            gemini_client.post("/v1/gemini/chat/completions", json={
                "model": "gemini-3-flash", "stream": False,
                "messages": [{"role": "user", "content": "My name is John"}],
            }, headers={**AUTH, **SID})

            r2 = gemini_client.post("/v1/gemini/chat/completions", json={
                "model": "gemini-3-flash", "stream": False,
                "messages": [{"role": "user", "content": "What is my name?"}],
            }, headers={**AUTH, **SID})
            assert r2.status_code == 200, r2.text

            data = SESSION_STORE.get("sess-gemini-1", {})
            assert data.get("gemini_cid") == "gem-cid-2"
            assert data.get("gemini_session_state") == {"turn": 2}

    def test_stream_session_persists(self, gemini_client):
        with patch("core.routers.gemini.chat.ChatSession") as MockChatSession:
            mock_chat = MockChatSession.return_value
            mock_chat.cid = None
            mock_chat.session_state = None
            mock_chat.metadata = {}

            mock_client = gemini_client.app.state.gemini_client

            async def gen_stream_side(prompt=None, model=None, chat=None):
                chat.cid = "gem-stream-cid"
                chat.session_state = {"stream": True}
                chat.metadata = {"stream_meta": "yes"}
                yield MagicMock(text_delta="Stream response")

            mock_client.generate_content_stream = gen_stream_side

            r = gemini_client.post("/v1/gemini/chat/completions", json={
                "model": "gemini-3-flash", "stream": True,
                "messages": [{"role": "user", "content": "Stream test"}],
            }, headers={**AUTH, **SID})
            assert r.status_code == 200

            data = SESSION_STORE.get("sess-gemini-1", {})
            assert data.get("gemini_cid") == "gem-stream-cid"
            assert data.get("gemini_session_state") == {"stream": True}
