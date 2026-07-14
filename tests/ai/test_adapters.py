
from engine.ai.adapters.gemini import GeminiAIProvider
from engine.ai.provider import AIProvider
from engine.domain.ai import AIRequest, AIResponse, ContextPayload, ProviderCapabilities


class MockAIProvider(AIProvider):
    """Deterministic mock provider for unit testing."""

    def __init__(self, stubbed_response: str) -> None:
        self.stubbed_response = stubbed_response

    def generate(self, request: AIRequest) -> AIResponse:
        return AIResponse(
            content=self.stubbed_response,
            usage_metrics={"prompt_tokens": 10},
            finish_reason="stop",
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            structured_output=True,
            streaming_support=False,
            tool_calling=False,
            image_input=False,
            reasoning_support=False,
            context_window=8000,
        )


def test_mock_provider() -> None:
    provider = MockAIProvider(stubbed_response="Mocked Output")
    request = AIRequest(
        prompt="Hi",
        context=ContextPayload(serialized_context=""),
    )
    resp = provider.generate(request)
    assert resp.content == "Mocked Output"


def test_gemini_provider() -> None:
    provider = GeminiAIProvider()
    assert provider.capabilities().context_window > 0
    request = AIRequest(
        prompt="Hi",
        context=ContextPayload(serialized_context=""),
    )
    # Stub should return the stub message
    resp = provider.generate(request)
    assert "Gemini Stub Generated Content" in resp.content
