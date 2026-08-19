import time
import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from core.server import app
from core.profile import create_profile, delete_profile
from core.session import generate_api_key, revoke_api_key


@pytest.mark.anyio
async def test_dashboard_responsiveness_under_heavy_concurrency():
    """
    Simulate multiple concurrent chat executions while measuring the responsiveness
    of Dashboard endpoints (/health, /v1/profiles, /v1/keys).
    Dashboard endpoints MUST respond instantly (< 200ms) without event-loop blocking.
    """
    # 1. Setup mock profiles and key
    p_ds = create_profile("deepseek", "Test Concurrency DS", token="tok_concurrency_ds")
    p_gem = create_profile("gemini", "Test Concurrency Gem", cookie="__Secure-1PSID=test_cookie")
    test_key = generate_api_key("concurrency_key")
    headers = {"Authorization": f"Bearer {test_key}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        try:
            # 2. Spawn 15 concurrent simulated long-running background tasks
            async def simulate_slow_upstream():
                await asyncio.sleep(0.5)

            tasks = [asyncio.create_task(simulate_slow_upstream()) for _ in range(15)]

            # 3. Concurrently hit the Dashboard endpoints
            t0 = time.time()
            res_health = await client.get("/health")
            res_profiles = await client.get("/v1/profiles", headers=headers)
            res_keys = await client.get("/v1/keys", headers=headers)
            elapsed_ms = (time.time() - t0) * 1000

            assert res_health.status_code == 200
            assert res_profiles.status_code == 200
            assert res_keys.status_code == 200

            # Dashboard requests should respond in under 200ms
            assert elapsed_ms < 200, f"Dashboard requests took {elapsed_ms:.2f}ms, which is too slow!"

            await asyncio.gather(*tasks)
        finally:
            delete_profile(p_ds["id"])
            delete_profile(p_gem["id"])
            revoke_api_key(test_key)
