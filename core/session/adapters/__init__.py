from .base import BaseSessionAdapter
from .deepseek import DeepSeekAdapter
from .gemini import GeminiAdapter

_ADAPTER_REGISTRY: dict[str, BaseSessionAdapter] = {}

def _register(adapter: BaseSessionAdapter):
    _ADAPTER_REGISTRY[adapter.scope] = adapter

_register(DeepSeekAdapter())
_register(GeminiAdapter())

def get_adapter(provider: str) -> BaseSessionAdapter:
    return _ADAPTER_REGISTRY.get(provider, BaseSessionAdapter())

def list_adapters() -> list[str]:
    return list(_ADAPTER_REGISTRY.keys())

