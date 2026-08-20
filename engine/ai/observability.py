"""Provider-boundary observability hook.

Isolates the "which concrete adapter class -> human-readable label" mapping
so ``engine.ai.executor.PromptExecutor`` itself stays a two-line diff. An
explicit type -> label table is used instead of an ``AIProvider.protocol``
abstract property, to avoid rippling an ABC change into all four adapters
(and every test that constructs ``MockAIProvider``) for what is otherwise a
purely cosmetic label.
"""

from engine.ai.adapters.anthropic import AnthropicAIProvider
from engine.ai.adapters.gemini import GeminiAIProvider
from engine.ai.adapters.ollama import OllamaAIProvider
from engine.ai.adapters.openai_compatible import OpenAICompatibleAIProvider
from engine.ai.provider import AIProvider
from engine.domain.ai import AIResponse
from shared.observability.usage_context import record_usage

_PROVIDER_LABELS: dict[type[AIProvider], str] = {
    GeminiAIProvider: "gemini",
    AnthropicAIProvider: "anthropic",
    OllamaAIProvider: "ollama",
    OpenAICompatibleAIProvider: "openai_compatible",
}


def label_provider(provider: AIProvider) -> str:
    """Return a human-readable label for a provider instance.

    Falls back to the lowercased class name for providers with no explicit
    entry (e.g. ``MockAIProvider`` in tests), rather than raising.
    """
    return _PROVIDER_LABELS.get(type(provider), type(provider).__name__.lower())


def capture_response_usage(provider: AIProvider, response: AIResponse) -> None:
    """Report one provider call's token usage to the active usage capture, if any.

    ``usage_metrics`` only carries ``prompt_tokens``/``completion_tokens`` keys
    today (no ``total_tokens``), and some providers (e.g. the test suite's
    ``MockAIProvider``) omit ``completion_tokens`` entirely -- ``.get(key, 0)``
    defaults are load-bearing here, not optional.
    """
    usage = response.usage_metrics
    record_usage(
        provider=label_provider(provider),
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
    )
