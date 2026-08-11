import logging
from typing import Optional
from gemini_webapi import GeminiClient
from core.utils import parse_cookie

logger = logging.getLogger(__name__)


class GeminiClientPool:
    def __init__(self):
        self._clients: dict[str, GeminiClient] = {}

    async def get_or_create_client(self, profile: dict) -> GeminiClient:
        pid = profile["id"]
        cookie_str = profile.get("cookie", "")
        secure_1psid = parse_cookie(cookie_str, "__Secure-1PSID") or parse_cookie(cookie_str, "__Secure-3PSID") or parse_cookie(cookie_str, "SID")
        secure_1psidts = parse_cookie(cookie_str, "__Secure-1PSIDTS") or parse_cookie(cookie_str, "__Secure-3PSIDTS")

        if not secure_1psid:
            raise ValueError(f"Gemini profile '{pid}' has invalid cookie (missing __Secure-1PSID, __Secure-3PSID, or SID).")

        # Reuse existing client if initialized
        if pid in self._clients:
            return self._clients[pid]

        client = GeminiClient(secure_1psid=secure_1psid, secure_1psidts=secure_1psidts)
        try:
            await client.init(timeout=30, auto_close=False)
            logger.info("[GeminiPool] Profile '%s' initialized successfully (status: %s).", pid, getattr(client, "account_status", None))
        except Exception as e:
            logger.error("[GeminiPool] Init failed for profile '%s': %s", pid, e)
            raise

        self._clients[pid] = client
        return client

    def get_client(self, profile_id: str) -> Optional[GeminiClient]:
        return self._clients.get(profile_id)

    async def close_all(self):
        for pid, client in list(self._clients.items()):
            try:
                await client.close()
            except Exception as e:
                logger.error("[GeminiPool] Error closing client for profile '%s': %s", pid, e)
        self._clients.clear()


gemini_pool = GeminiClientPool()
