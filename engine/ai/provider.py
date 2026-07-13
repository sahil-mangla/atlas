"""AI Provider interface definitions."""

from abc import ABC, abstractmethod

from engine.domain.ai import AIRequest, AIResponse, ProviderCapabilities


class AIProvider(ABC):
    """Abstract dependency inversion boundary for all AI model access."""

    @abstractmethod
    def generate(self, request: AIRequest) -> AIResponse:
        """Process a standardized AI generation request.

        Args:
            request: Formatted deterministic AIRequest containing context and prompts.

        Returns:
            Provider-agnostic normalized AIResponse.

        Raises:
            AIProviderException: If the underlying model provider encounters an error.
        """
        pass

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Describe the feature set of this provider implementation."""
        pass
