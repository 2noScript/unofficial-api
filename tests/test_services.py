import pytest
from core.services.base import BaseProviderStrategy
from core.services.deepseek_strategy import DeepSeekStrategy
from core.services.gemini_strategy import GeminiStrategy
from core.services.chat_service import chat_service


def test_strategy_instantiation():
    ds_strat = DeepSeekStrategy()
    assert ds_strat.provider_name == "deepseek"

    gem_strat = GeminiStrategy()
    assert gem_strat.provider_name == "gemini"


def test_chat_service_session_check():
    assert chat_service._has_provider_session("deepseek", {"deepseek_chat_session_id": "ds123"}) is True
    assert chat_service._has_provider_session("deepseek", {}) is False

    assert chat_service._has_provider_session("gemini", {"gemini_cid": "gem123"}) is True
    assert chat_service._has_provider_session("gemini", {}) is False
