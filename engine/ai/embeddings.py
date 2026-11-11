"""Embedding provider interface.

Deliberately separate from ``AIProvider``: not every generation protocol has an
embeddings API (Anthropic does not), so embeddings must not be a required
method on the shared generation boundary. Implementations also satisfy the
structural ``Embedder`` protocol that ``engine.knowledge`` depends on, which is
how knowledge retrieval gets vectors without importing ``engine.ai``.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence


class EmbeddingProvider(ABC):
    """Abstract boundary for turning text into vectors."""

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Stable identifier of the vector space, e.g. ``GEMINI:model-name``.

        Vectors from different ids are never compared, so changing the model
        simply causes entries to be re-embedded.
        """

    @abstractmethod
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one vector per input text, in order.

        Raises:
            AIProviderException: The provider rejected the request or returned
                a malformed response.
        """
