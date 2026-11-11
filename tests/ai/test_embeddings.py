"""Embedding provider adapters and factory."""

from typing import Any

import pytest

from engine.ai.adapters import ollama as ollama_module
from engine.ai.adapters import openai_compatible as openai_module
from engine.ai.adapters._http import parse_embeddings
from engine.ai.adapters.ollama import OllamaEmbeddingProvider
from engine.ai.adapters.openai_compatible import OpenAICompatibleEmbeddingProvider
from engine.ai.config import ProviderConfig
from engine.ai.embedding_factory import EmbeddingFactory
from engine.ai.exceptions import AIProviderException


def test_parse_embeddings_rejects_wrong_count_and_empty_vectors() -> None:
    assert parse_embeddings([[1, 2], [3, 4]], 2) == [[1.0, 2.0], [3.0, 4.0]]
    with pytest.raises(AIProviderException):
        parse_embeddings([[1.0]], 2)
    with pytest.raises(AIProviderException):
        parse_embeddings([[]], 1)
    with pytest.raises(AIProviderException):
        parse_embeddings(None, 1)


def test_ollama_embeddings_call_api_embed(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def fake_post(
        url: str, payload: dict[str, Any], _headers: dict[str, str], **_kwargs: object
    ) -> dict[str, Any]:
        seen.update(url=url, payload=payload)
        return {"embeddings": [[0.1, 0.2], [0.3, 0.4]]}

    monkeypatch.setattr(ollama_module, "post_json", fake_post)
    provider = OllamaEmbeddingProvider(
        ProviderConfig(protocol="OLLAMA", model="nomic-embed-text")
    )

    vectors = provider.embed(["a", "b"])

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]
    assert seen["url"] == "http://localhost:11434/api/embed"
    assert seen["payload"] == {"model": "nomic-embed-text", "input": ["a", "b"]}
    assert provider.model_id == "OLLAMA:nomic-embed-text"


def test_ollama_embeddings_require_a_model() -> None:
    with pytest.raises(AIProviderException, match="ATLAS_EMBEDDING_MODEL"):
        OllamaEmbeddingProvider(ProviderConfig(protocol="OLLAMA"))


def test_openai_embeddings_restore_input_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, Any] = {}

    def fake_post(
        url: str, _payload: dict[str, Any], headers: dict[str, str], **_kwargs: object
    ) -> dict[str, Any]:
        seen.update(url=url, headers=headers)
        return {
            "data": [
                {"index": 1, "embedding": [0.3, 0.4]},
                {"index": 0, "embedding": [0.1, 0.2]},
            ]
        }

    monkeypatch.setattr(openai_module, "post_json", fake_post)
    provider = OpenAICompatibleEmbeddingProvider(
        ProviderConfig(
            protocol="OPENAI_COMPATIBLE",
            endpoint="https://api.example.com/v1/",
            model="text-embedding-3-small",
            api_key="k",
        )
    )

    assert provider.embed(["a", "b"]) == [[0.1, 0.2], [0.3, 0.4]]
    assert seen["url"] == "https://api.example.com/v1/embeddings"
    assert seen["headers"] == {"Authorization": "Bearer k"}


def test_openai_embeddings_require_endpoint_and_model() -> None:
    with pytest.raises(AIProviderException):
        OpenAICompatibleEmbeddingProvider(
            ProviderConfig(protocol="OPENAI_COMPATIBLE", model="m")
        )


def test_factory_has_no_embeddings_for_anthropic() -> None:
    with pytest.raises(AIProviderException, match="no embeddings support"):
        EmbeddingFactory().resolve(ProviderConfig(protocol="ANTHROPIC", model="m"))


def test_factory_resolves_registered_protocols() -> None:
    provider = EmbeddingFactory().resolve(
        ProviderConfig(protocol="ollama", model="nomic-embed-text")
    )

    assert isinstance(provider, OllamaEmbeddingProvider)
