import json
import logging
import uuid

from curl_cffi.requests import AsyncSession

logger = logging.getLogger(__name__)

CHAT_URL = "https://grok.com/rest/app-chat/conversations/new"


def _build_headers(sso_token: str) -> dict:
    return {
        "accept": "*/*",
        "accept-language": "en-GB,en;q=0.9",
        "content-type": "application/json",
        "origin": "https://grok.com",
        "referer": "https://grok.com/",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "x-xai-request-id": str(uuid.uuid4()),
        "Cookie": f"sso={sso_token}; sso-rw={sso_token}",
    }


def _build_payload(message: str) -> dict:
    return {
        "temporary": False,
        "modelName": "grok-3",
        "message": message,
        "fileAttachments": [],
        "imageAttachments": [],
        "disableSearch": False,
        "enableImageGeneration": False,
        "returnImageBytes": False,
        "returnRawGrokInXaiRequest": False,
        "enableImageStreaming": False,
        "imageGenerationCount": 0,
        "forceConcise": False,
        "enableSideBySide": True,
        "isPreset": False,
        "sendFinalMetadata": True,
    }


class GrokClient:
    def __init__(self, cookies_str: str = ""):
        self._token = ""
        for c in cookies_str.split(";"):
            c = c.strip()
            if c.startswith("sso="):
                self._token = c[4:]
                break

    async def send_message(self, message: str) -> str:
        headers = _build_headers(self._token)
        payload = _build_payload(message)

        async with AsyncSession() as session:
            async with session.post(
                CHAT_URL,
                headers=headers,
                json=payload,
                stream=True,
            ) as response:
                response.raise_for_status()
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
                        data = json.loads(text)
                        result = data.get("result", {})
                        resp_data = result.get("response", {})
                        if "modelResponse" in resp_data:
                            return resp_data["modelResponse"].get("message", "")
                        token = resp_data.get("token", "")
                        if token:
                            full += token
                    except json.JSONDecodeError:
                        continue
                return full
