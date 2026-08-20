"""Tests for the provider-boundary observability hook."""

from engine.ai.adapters.anthropic import AnthropicAIProvider
from engine.ai.adapters.gemini import GeminiAIProvider
from engine.ai.adapters.ollama import OllamaAIProvider
from engine.ai.adapters.openai_compatible import OpenAICompatibleAIProvider
from engine.ai.config import ProviderConfig
from engine.ai.observability import capture_response_usage, label_provider
from engine.domain.ai import AIResponse
from shared.observability.usage_context import finish_capture, start_capture
from tests.ai.test_adapters import MockAIProvider


def _config() -> ProviderConfig:
    return ProviderConfig(model="m", endpoint="http://localhost", api_key="k")


def test_label_provider_for_each_real_adapter() -> None:
    assert label_provider(GeminiAIProvider(_config())) == "gemini"
    assert label_provider(AnthropicAIProvider(_config())) == "anthropic"
    assert label_provider(OllamaAIProvider(_config())) == "ollama"
    assert label_provider(OpenAICompatibleAIProvider(_config())) == "openai_compatible"


def test_label_provider_falls_back_to_lowercased_class_name_for_unmapped_provider() -> (
    None
):
    assert label_provider(MockAIProvider("{}")) == "mockaiprovider"


def test_capture_response_usage_is_a_safe_noop_with_no_active_capture() -> None:
    response = AIResponse(
        content="{}", usage_metrics={"prompt_tokens": 5}, finish_reason="stop"
    )
    capture_response_usage(MockAIProvider("{}"), response)


def test_capture_response_usage_records_into_active_capture() -> None:
    response = AIResponse(
        content="{}",
        usage_metrics={"prompt_tokens": 7, "completion_tokens": 3},
        finish_reason="stop",
    )
    token = start_capture()
    capture_response_usage(MockAIProvider("{}"), response)
    calls = finish_capture(token)

    assert len(calls) == 1
    assert calls[0].provider == "mockaiprovider"
    assert calls[0].prompt_tokens == 7
    assert calls[0].completion_tokens == 3


def test_capture_response_usage_defaults_missing_completion_tokens_to_zero() -> None:
    """``MockAIProvider`` itself omits ``completion_tokens`` -- confirm the
    ``.get(key, 0)`` default in ``capture_response_usage`` is load-bearing."""
    response = AIResponse(
        content="{}", usage_metrics={"prompt_tokens": 10}, finish_reason="stop"
    )
    token = start_capture()
    capture_response_usage(MockAIProvider("{}"), response)
    calls = finish_capture(token)

    assert calls[0].completion_tokens == 0
