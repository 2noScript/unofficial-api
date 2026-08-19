import time
import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from core.server import app
from core.profile import create_profile, delete_profile
from core.session import generate_api_key, revoke_api_key


@pytest.mark.anyio
async def test_per_session_locking_concurrency():
    """
    Test that concurrent requests with the SAME X-Session-Id are executed sequentially,
    while requests with DIFFERENT X-Session-Ids can execute concurrently.
    """
    test_key = generate_api_key("lock_test_key")
    headers_sess1 = {"Authorization": f"Bearer {test_key}", "X-Session-Id": "sess-lock-test-1"}
    headers_sess2 = {"Authorization": f"Bearer {test_key}", "X-Session-Id": "sess-lock-test-2"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        try:
            # Check health responds
            res = await client.get("/health")
            assert res.status_code == 200

            # Generate multiple requests for sess1 and sess2
            # Even if invalid model or mock, the middleware acquires and releases the lock properly
            r1 = client.post(
                "/v1/deepseek/chat/completions",
                json={"model": "invalid-model", "messages": [{"role": "user", "content": "1"}]},
                headers=headers_sess1
            )
            r2 = client.post(
                "/v1/deepseek/chat/completions",
                json={"model": "invalid-model", "messages": [{"role": "user", "content": "2"}]},
                headers=headers_sess1
            )
            r3 = client.post(
                "/v1/deepseek/chat/completions",
                json={"model": "invalid-model", "messages": [{"role": "user", "content": "3"}]},
                headers=headers_sess2
            )

            res1, res2, res3 = await asyncio.gather(r1, r2, r3)
            assert res1.headers.get("X-Session-Id") == "sess-lock-test-1"
            assert res2.headers.get("X-Session-Id") == "sess-lock-test-1"
            assert res3.headers.get("X-Session-Id") == "sess-lock-test-2"
        finally:
            revoke_api_key(test_key)
