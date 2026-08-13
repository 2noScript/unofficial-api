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


def test_deepseek_is_retryable_error_only_401():
    ds_strat = DeepSeekStrategy()
    # 401 / Unauthorized -> True (Deactivates profile)
    assert ds_strat.is_retryable_error("HTTP 401: Unauthorized token") is True
    assert ds_strat.is_retryable_error("Invalid token") is True
    assert ds_strat.is_retryable_error("Token expired") is True
    assert ds_strat.is_retryable_error("Unauthenticated user") is True

    # 429 / 403 / 500 / Rate limit -> False (Should NOT deactivate profile)
    assert ds_strat.is_retryable_error("HTTP 429: Too Many Requests") is False
    assert ds_strat.is_retryable_error("HTTP 403: Forbidden") is False
    assert ds_strat.is_retryable_error("Rate limit exceeded") is False
    assert ds_strat.is_retryable_error("Server error 500") is False

