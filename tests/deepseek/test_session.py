import os
from unittest.mock import patch

os.environ.setdefault("DEEPSEEK_COOKIE", "ds_session_id=test-session")
os.environ.setdefault("DEEPSEEK_AUTH_TOKEN", "test-auth-token")

AUTH = {"Authorization": "Bearer ua-test-test-test"}
SID = {"X-Session-Id": "sess-ds-1"}


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

            client.post("/v1/deepseek/chat/completions", json={
                "model": "deepseek-v3", "stream": False,
                "messages": [{"role": "user", "content": "Check context"}],
            }, headers={**AUTH, **SID})
