"""Tests for registry-based AI provider resolution."""

import pytest

from engine.ai.config import ProviderConfig
from engine.ai.exceptions import AIProviderException
from engine.ai.factory import ProviderFactory
from tests.ai.test_adapters import MockAIProvider


def test_provider_factory_resolves_registered_provider_case_insensitively() -> None:
    provider = MockAIProvider("{}")
    factory = ProviderFactory({"TEST": lambda _config, _settings: provider})

    resolved = factory.create("test", ProviderConfig(protocol="TEST"))

    assert resolved is provider


def test_provider_factory_rejects_unknown_provider() -> None:
    factory = ProviderFactory({})

    with pytest.raises(AIProviderException, match="Unknown AI Provider: TEST"):
        factory.create("TEST")
