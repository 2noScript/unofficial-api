import logging
import re

import orjson

from app.control.model.enums import ModeId
from app.control.proxy.models import ProxyLease
from app.dataplane.reverse.protocol.xai_chat import build_chat_payload
from app.dataplane.proxy.adapters.headers import build_http_headers
from app.dataplane.proxy.adapters.session import ResettableSession
from app.dataplane.reverse.runtime.endpoint_table import CHAT

logger = logging.getLogger(__name__)


def _extract_sso(cookies_str: str) -> str:
    m = re.search(r"(?:^|;\s*)sso=([^;]+)", cookies_str)
    return m.group(1) if m else ""


class GrokClient:
    def __init__(self, cookies_str: str = "", user_agent: str = "", browser: str = ""):
        self._cookies_str = cookies_str
        self._sso_token = _extract_sso(cookies_str)
        self._user_agent = user_agent
        self._browser = browser
        self._lease = ProxyLease(
            lease_id="",
            user_agent=user_agent,
            cf_cookies=cookies_str,
        )

    async def send_message(
        self,
        message: str,
        mode_id: ModeId = ModeId.AUTO,
    ) -> str:
        payload = build_chat_payload(message=message, mode_id=mode_id)
        headers = build_http_headers(self._sso_token, lease=self._lease)

        async with ResettableSession(
            lease=self._lease,
            browser_override=self._browser or None,
        ) as session:
            response = await session.post(
                CHAT,
                headers=headers,
                data=orjson.dumps(payload),
                timeout=120,
                stream=True,
            )
            if response.status_code != 200:
                try:
                    body_bytes = await response.acontent()
                    body = (body_bytes or b"").decode("utf-8", "replace")[:400]
                except Exception as e:
                    body = f"<read_error: {e}>"
                raise RuntimeError(
                    f"Chat upstream returned {response.status_code}; body={body}"
                )
            full = ""
            async for line in response.aiter_lines():
                text = line.strip()
                if not text:
                    continue
                if text == "data: [DONE]":
                    break
                if text.startswith("data:"):
                    text = text[5:].strip()
                if not text.startswith("{"):
                    continue
                try:
                    data = orjson.loads(text)
                    result = data.get("result", {})
                    resp_data = result.get("response", {})
                    if "modelResponse" in resp_data:
                        return resp_data["modelResponse"].get("message", "")
                    token = resp_data.get("token", "")
                    if token:
                        full += token
                except Exception:
                    continue
            return full
