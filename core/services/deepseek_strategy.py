import os
import asyncio
from typing import Any, AsyncGenerator
from deepseek_api import DeepSeek
from core.services.base import BaseProviderStrategy


class DeepSeekStrategy(BaseProviderStrategy):
    """DeepSeek Provider Strategy implementation."""

    @property
    def provider_name(self) -> str:
        return "deepseek"

    async def get_or_create_client(self, profile: dict | None, request: Any) -> Any:
        auth_token = profile.get("token", "") if profile else ""
        if not auth_token:
            raise ValueError("DeepSeek profile has no valid token.")
        if not auth_token.startswith("Bearer "):
            auth_token = f"Bearer {auth_token}"
        return await asyncio.to_thread(DeepSeek, auth_token)

    async def execute_chat(
        self, client: Any, prompt: str, model: str, session_kwargs: dict
    ) -> tuple[str, str]:
        chat = await asyncio.to_thread(client.new_session, **session_kwargs)
        session_kwargs["chat"] = chat
        result = await asyncio.to_thread(chat.send_message, prompt, model=model)

        if not result.get("ok"):
            err_msg = result.get("content", "Unknown error")
            if isinstance(err_msg, (bytes, bytearray)):
                err_msg = err_msg.decode("utf-8", errors="replace")
            raise RuntimeError(err_msg)

        content = result.get("content", {})
        if isinstance(content, dict):
            return content.get("response", ""), content.get("thinking", "")
        return str(content), ""

    async def execute_stream(
        self, client: Any, prompt: str, model: str, session_kwargs: dict
    ) -> AsyncGenerator[str, None]:
        chat = await asyncio.to_thread(client.new_session, **session_kwargs)
        session_kwargs["chat"] = chat
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()


        def run_stream() -> dict:
            try:
                for event_type, content in chat.send_message_stream(prompt, model=model):
                    if event_type == "error":
                        return {"ok": False, "content": content}
                    elif event_type in ("content", "thought"):
                        loop.call_soon_threadsafe(queue.put_nowait, content)
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "content": str(e)}

        t = loop.run_in_executor(None, run_stream)

        while True:
            get_task = asyncio.create_task(queue.get())
            done, _ = await asyncio.wait([get_task, t], return_when=asyncio.FIRST_COMPLETED)

            if get_task in done:
                chunk_text = get_task.result()
                yield chunk_text
            else:
                get_task.cancel()
                res = t.result()
                if not res.get("ok"):
                    raise RuntimeError(res.get("content", "Stream error"))
                while not queue.empty():
                    yield queue.get_nowait()
                break

    async def handle_profile_cleanup(self, profile_id: str | None) -> None:
        pass

    def is_retryable_error(self, err: str | Exception) -> bool:
        import re
        msg = str(err).lower()
        text_keywords = ("unauthorized", "unauthenticated", "invalid token", "token expired", "expired token")
        if any(kw in msg for kw in text_keywords):
            return True
        return bool(re.search(r'\b401\b', msg))


