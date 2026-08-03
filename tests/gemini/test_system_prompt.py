import uuid
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

AUTH = {"Authorization": "Bearer ua-test-key"}
SID = {"x-session-id": "sess-sys-prompt-1"}
SESSION_STORE = {}


@pytest.fixture
def gemini_app():
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
def client(gemini_app):
    SESSION_STORE.clear()
    with TestClient(gemini_app) as c:
        yield c


class TestGeminiSystemPrompt:
    def test_system_prompt_formatting_on_first_turn(self, client):
        mock_client = client.app.state.gemini_client
        captured_prompts = []

        async def gen_side(prompt=None, model=None, chat=None):
            captured_prompts.append(prompt)
            return MagicMock(text="I am a Python assistant.", thoughts="")

        mock_client.generate_content = AsyncMock(side_effect=gen_side)

        resp = client.post(
            "/v1/gemini/chat/completions",
            json={
                "model": "gemini-3-flash",
                "stream": False,
                "messages": [
                    {"role": "system", "content": "You are a Python expert assistant."},
                    {"role": "user", "content": "How do I reverse a list?"},
                ],
            },
            headers={**AUTH, **SID},
        )

        assert resp.status_code == 200
        assert len(captured_prompts) == 1
        prompt_sent = captured_prompts[0]

        # Verify system prompt was formatted into prompt sent to Gemini
        assert "[System Instruction]" in prompt_sent
        assert "You are a Python expert assistant." in prompt_sent
        assert "[Current message]" in prompt_sent
        assert "How do I reverse a list?" in prompt_sent

    def test_system_prompt_persists_in_fallback(self, client):
        mock_client = client.app.state.gemini_client
        captured_prompts = []

        async def gen_side(prompt=None, model=None, chat=None):
            captured_prompts.append(prompt)
            n = len(captured_prompts)
            if n == 1:
                chat.cid = "sys-cid-1"
                chat.metadata = {"meta": "1"}
                return MagicMock(text="Use list.reverse() or slicing [::-1].", thoughts="")
            if n == 2:
                # Simulate session expiration / error on turn 2
                raise Exception("Session expired or missing")
            chat.cid = None
            chat.metadata = {}
            return MagicMock(text="Slicing creates a new reversed copy.", thoughts="")

        mock_client.generate_content = AsyncMock(side_effect=gen_side)

        # Turn 1
        r1 = client.post(
            "/v1/gemini/chat/completions",
            json={
                "model": "gemini-3-flash",
                "stream": False,
                "messages": [
                    {"role": "system", "content": "You are a concise Python bot."},
                    {"role": "user", "content": "Reverse list syntax?"},
                ],
            },
            headers={**AUTH, **SID},
        )
        assert r1.status_code == 200

        # Turn 2: triggers fallback, should reconstruct history INCLUDING system prompt
        r2 = client.post(
            "/v1/gemini/chat/completions",
            json={
                "model": "gemini-3-flash",
                "stream": False,
                "messages": [
                    {"role": "system", "content": "You are a concise Python bot."},
                    {"role": "user", "content": "Reverse list syntax?"},
                    {"role": "assistant", "content": "Use list.reverse() or slicing [::-1]."},
                    {"role": "user", "content": "What does slicing do?"},
                ],
            },
            headers={**AUTH, **SID},
        )
        assert r2.status_code == 200

        # Look at prompt 3 (retry prompt after fallback)
        fallback_prompt = captured_prompts[2]
        assert "[System Instruction]" in fallback_prompt
        assert "You are a concise Python bot." in fallback_prompt
        assert "[Previous conversation]" in fallback_prompt
        assert "User: Reverse list syntax?" in fallback_prompt
        assert "[Current message]" in fallback_prompt
        assert "What does slicing do?" in fallback_prompt

    def test_system_prompt_with_streaming(self, client):
        mock_client = client.app.state.gemini_client
        captured_prompts = []

        async def gen_stream_side(prompt=None, model=None, chat=None):
            captured_prompts.append(prompt)
            yield MagicMock(text_delta="Python slicing [::-1]")

        mock_client.generate_content_stream = gen_stream_side

        resp = client.post(
            "/v1/gemini/chat/completions",
            json={
                "model": "gemini-3-flash",
                "stream": True,
                "messages": [
                    {"role": "system", "content": "Strictly code output only."},
                    {"role": "user", "content": "Reverse list"},
                ],
            },
            headers={**AUTH, **SID},
        )

        assert resp.status_code == 200
        assert len(captured_prompts) == 1
        prompt_sent = captured_prompts[0]

        assert "[System Instruction]" in prompt_sent
        assert "Strictly code output only." in prompt_sent
        assert "Reverse list" in prompt_sent
