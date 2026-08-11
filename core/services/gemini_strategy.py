from typing import Any, AsyncGenerator
from fastapi.responses import JSONResponse
from gemini_webapi import GeminiClient, ChatSession
from core.services.base import BaseProviderStrategy
from core.routers.gemini.pool import gemini_pool
from core.routers.gemini.helpers import _require_client


class GeminiStrategy(BaseProviderStrategy):
    """Gemini Provider Strategy implementation."""

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def get_or_create_client(self, profile: dict | None, request: Any) -> Any:
        app_client = getattr(getattr(request, "app", None), "state", None)
        mocked_client = getattr(app_client, "gemini_client", None) if app_client else None
        if mocked_client is not None:
            return mocked_client

        if profile:
            return await gemini_pool.get_or_create_client(profile)
        client = _require_client(request)
        if isinstance(client, JSONResponse):
            raise RuntimeError("No active Gemini profile available.")
        return client

    async def execute_chat(
        self, client: Any, prompt: str, model: str, session_kwargs: dict
    ) -> tuple[str, str]:
        chat = session_kwargs.get("chat")
        if not chat:
            chat = ChatSession(geminiclient=client)
        output = await client.generate_content(prompt=prompt, model=model, chat=chat)
        return output.text or "", output.thoughts or ""

    async def execute_stream(
        self, client: Any, prompt: str, model: str, session_kwargs: dict
    ) -> AsyncGenerator[str, None]:
        chat = session_kwargs.get("chat")
        if not chat:
            chat = ChatSession(geminiclient=client)
        gen = client.generate_content_stream(prompt=prompt, model=model, chat=chat)
        async for chunk in gen:
            delta = chunk.text_delta
            if delta:
                yield delta

    async def handle_profile_cleanup(self, profile_id: str | None) -> None:
        if profile_id and profile_id in gemini_pool._clients:
            del gemini_pool._clients[profile_id]

    def is_retryable_error(self, err: str | Exception) -> bool:
        msg = str(err).lower()
        if "session is not authenticated" in msg:
            return False
        keywords = ("401", "403", "429", "unauthorized", "invalid cookie", "rate limit", "too many requests", "40300")
        return any(kw in msg for kw in keywords)
