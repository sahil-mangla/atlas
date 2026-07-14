"""Gemini adapter implementation of the AIProvider."""

from engine.ai.exceptions import AIProviderException
from engine.ai.provider import AIProvider
from engine.domain.ai import AIRequest, AIResponse, ProviderCapabilities


class GeminiAIProvider(AIProvider):
    """Adapter bridging ATLAS AIProvider protocol with Google's Gemini SDK."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the Gemini provider.

        Args:
            api_key: The API key for authentication. If None, it assumes the SDK
                will pull from the environment.
        """
        self.api_key = api_key

    def generate(self, request: AIRequest) -> AIResponse:
        """Process an AIRequest via Gemini.

        This implementation ensures Gemini-specific types (like GenerateContentResponse)
        are constrained to this module and mapped back to AIResponse.
        """
        try:
            # In a real implementation, we would construct the Gemini SDK payload
            # using request.prompt, request.context.serialized_context, request.parameters
            # and invoke the SDK.

            # This is a stub placeholder for Stage 11 scaffolding
            return AIResponse(
                content="[Gemini Stub Generated Content]",
                usage_metrics={"prompt_tokens": 0, "completion_tokens": 0},
                finish_reason="stop",
            )
        except Exception as e:
            raise AIProviderException(f"Gemini provider error: {e}") from e

    def capabilities(self) -> ProviderCapabilities:
        """Describe Gemini's capabilities."""
        return ProviderCapabilities(
            structured_output=True,
            streaming_support=True,
            tool_calling=True,
            image_input=True,
            reasoning_support=False,  # Update when applicable
            context_window=2_000_000,
        )
