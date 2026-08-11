import os
from typing import Any, AsyncGenerator
from deepseek_api import DeepSeek
from core.services.base import BaseProviderStrategy


class DeepSeekStrategy(BaseProviderStrategy):
    """DeepSeek Provider Strategy implementation."""

    @property
    def provider_name(self) -> str:
        return "deepseek"

    async def get_or_create_client(self, profile: dict | None, request: Any) -> Any:
        auth_token = profile.get("token", "") if profile else os.environ.get("DEEPSEEK_AUTH_TOKEN")
        if not auth_token:
            raise ValueError("DeepSeek credentials not found. Create a DeepSeek profile or set DEEPSEEK_AUTH_TOKEN.")
        if not auth_token.startswith("Bearer "):
            auth_token = f"Bearer {auth_token}"
        return DeepSeek(auth_token)

    async def execute_chat(
        self, client: Any, prompt: str, model: str, session_kwargs: dict
    ) -> tuple[str, str]:
        chat = client.new_session(**session_kwargs)
        result = chat.send_message(prompt, model=model)

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
        chat = client.new_session(**session_kwargs)
        # Assuming DeepSeek streaming yields chunks
        gen = chat.send_message(prompt, model=model, stream=True)
        if hasattr(gen, "__aiter__"):
            async for chunk in gen:
                if isinstance(chunk, dict):
                    yield chunk.get("text", "")
                else:
                    yield str(chunk)
        elif hasattr(gen, "__iter__"):
            for chunk in gen:
                if isinstance(chunk, dict):
                    yield chunk.get("text", "")
                else:
                    yield str(chunk)

    async def handle_profile_cleanup(self, profile_id: str | None) -> None:
        pass

    def is_retryable_error(self, err: str | Exception) -> bool:
        msg = str(err).lower()
        keywords = ("401", "403", "429", "unauthorized", "unauthenticated", "invalid token", "rate limit", "too many requests", "40300")
        return any(kw in msg for kw in keywords)
