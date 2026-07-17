"""Registry-driven protocol adapter construction."""

from collections.abc import Callable, Mapping
from types import MappingProxyType

from engine.ai.adapters.anthropic import AnthropicAIProvider
from engine.ai.adapters.gemini import GeminiAIProvider
from engine.ai.adapters.ollama import OllamaAIProvider
from engine.ai.adapters.openai_compatible import OpenAICompatibleAIProvider
from engine.ai.config import ProviderConfig
from engine.ai.exceptions import AIProviderException
from engine.ai.provider import AIProvider
from engine.config import Settings

ProtocolConstructor = Callable[[ProviderConfig, Settings | None], AIProvider]


def _create_gemini(config: ProviderConfig, settings: Settings | None) -> AIProvider:
    return GeminiAIProvider(config, settings)


def _create_openai_compatible(
    config: ProviderConfig, _settings: Settings | None
) -> AIProvider:
    return OpenAICompatibleAIProvider(config)


def _create_anthropic(config: ProviderConfig, _settings: Settings | None) -> AIProvider:
    return AnthropicAIProvider(config)


def _create_ollama(config: ProviderConfig, _settings: Settings | None) -> AIProvider:
    return OllamaAIProvider(config)


class ProtocolFactory:
    """Resolve registered protocol adapters without provider-specific branching."""

    def __init__(
        self, registry: Mapping[str, ProtocolConstructor] | None = None
    ) -> None:
        default_registry: Mapping[str, ProtocolConstructor] = {
            "GEMINI": _create_gemini,
            "OPENAI_COMPATIBLE": _create_openai_compatible,
            "ANTHROPIC": _create_anthropic,
            "OLLAMA": _create_ollama,
        }
        registrations = registry if registry is not None else default_registry
        self._registry = MappingProxyType(
            {
                protocol.upper(): constructor
                for protocol, constructor in registrations.items()
            }
        )

    def create(
        self,
        protocol: str,
        config: ProviderConfig | None = None,
        settings: Settings | None = None,
    ) -> AIProvider:
        """Construct the adapter registered for ``protocol``."""
        resolved_config = config or ProviderConfig(protocol=protocol)
        constructor = self._registry.get(protocol.upper())
        if constructor is None:
            raise AIProviderException(
                f"Unknown AI Provider: {protocol} (Unknown AI Protocol: {protocol})"
            )
        return constructor(resolved_config, settings)

    def resolve(
        self, config: ProviderConfig, settings: Settings | None = None
    ) -> AIProvider:
        """Resolve a configured protocol through the single runtime entry point."""
        return self.create(config.protocol, config, settings)


# Public compatibility name retained for integrations from phases 1-11.
ProviderFactory = ProtocolFactory
