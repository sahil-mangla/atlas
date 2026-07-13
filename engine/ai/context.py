"""Context assembly and compression strategies."""

from abc import ABC, abstractmethod

from engine.domain.ai import ContextPayload


class ContextStrategy(ABC):
    """Abstract interface for strategies that format or compress context payloads."""

    @abstractmethod
    def apply(self, context: ContextPayload) -> ContextPayload:
        """Apply a compression or formatting strategy to the context payload.

        Args:
            context: The raw immutable context payload assembled from repositories.

        Returns:
            A transformed or compressed context payload.
        """
        pass


class IdentityContextStrategy(ContextStrategy):
    """A passthrough strategy that performs no compression or mutation.

    Suitable for Stage 11 where projects are small enough to fit within
    the standard provider context window.
    """

    def apply(self, context: ContextPayload) -> ContextPayload:
        """Return the context unmodified."""
        return context
