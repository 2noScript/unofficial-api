from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator


class BaseProviderStrategy(ABC):
    """Abstract Strategy interface for AI providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider identifier ('deepseek', 'gemini')."""
        pass

    @abstractmethod
    async def get_or_create_client(self, profile: dict | None, request: Any) -> Any:
        """Initialize or retrieve the provider client instance."""
        pass

    @abstractmethod
    async def execute_chat(
        self, client: Any, prompt: str, model: str, session_kwargs: dict
    ) -> tuple[str, str]:
        """
        Execute non-streaming chat request.
        Returns tuple of (content_text, reasoning_thoughts).
        """
        pass

    @abstractmethod
    def execute_stream(
        self, client: Any, prompt: str, model: str, session_kwargs: dict
    ) -> AsyncGenerator[str, None]:
        """
        Execute streaming chat request.
        Yields text deltas.
        """
        pass

    @abstractmethod
    async def handle_profile_cleanup(self, profile_id: str | None) -> None:
        """Clean up provider client instance if profile fails."""
        pass

    def is_retryable_error(self, err: str | Exception) -> bool:
        """Determine if an error for this specific provider is a retryable/fatal auth failure."""
        return False
