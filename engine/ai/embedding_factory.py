"""Registry-driven embedding provider construction."""

from collections.abc import Callable, Mapping
from types import MappingProxyType

from engine.ai.adapters.gemini import GeminiEmbeddingProvider
from engine.ai.adapters.ollama import OllamaEmbeddingProvider
from engine.ai.adapters.openai_compatible import OpenAICompatibleEmbeddingProvider
from engine.ai.config import ProviderConfig
from engine.ai.embeddings import EmbeddingProvider
from engine.ai.exceptions import AIProviderException
from engine.config import Settings

EmbeddingConstructor = Callable[[ProviderConfig, Settings | None], EmbeddingProvider]


def _create_gemini(
    config: ProviderConfig, settings: Settings | None
) -> EmbeddingProvider:
    return GeminiEmbeddingProvider(config, settings)


def _create_openai_compatible(
    config: ProviderConfig, _settings: Settings | None
) -> EmbeddingProvider:
    return OpenAICompatibleEmbeddingProvider(config)


def _create_ollama(
    config: ProviderConfig, _settings: Settings | None
) -> EmbeddingProvider:
    return OllamaEmbeddingProvider(config)


class EmbeddingFactory:
    """Resolve embedding adapters; protocols without an embeddings API are absent.

    ANTHROPIC is intentionally not registered -- it has no embeddings endpoint.
    """

    def __init__(
        self, registry: Mapping[str, EmbeddingConstructor] | None = None
    ) -> None:
        default_registry: Mapping[str, EmbeddingConstructor] = {
            "GEMINI": _create_gemini,
            "OPENAI_COMPATIBLE": _create_openai_compatible,
            "OLLAMA": _create_ollama,
        }
        registrations = registry if registry is not None else default_registry
        self._registry = MappingProxyType(
            {protocol.upper(): ctor for protocol, ctor in registrations.items()}
        )

    def resolve(
        self, config: ProviderConfig, settings: Settings | None = None
    ) -> EmbeddingProvider:
        """Construct the embedding adapter registered for ``config.protocol``."""
        constructor = self._registry.get(config.protocol.upper())
        if constructor is None:
            supported = ", ".join(sorted(self._registry))
            raise AIProviderException(
                f"Protocol {config.protocol} has no embeddings support. Set "
                f"ATLAS_EMBEDDING_PROTOCOL to one of: {supported}."
            )
        return constructor(config, settings)
