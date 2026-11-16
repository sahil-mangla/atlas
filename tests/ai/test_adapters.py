import sys

import pytest

from atlas_eng.engine.ai.adapters.gemini import GeminiAIProvider, _flatten_schema
from atlas_eng.engine.ai.provider import AIProvider
from atlas_eng.engine.domain.ai import (
    AIRequest,
    AIResponse,
    ContextPayload,
    ProviderCapabilities,
)
from atlas_eng.engine.domain.ai_drafts import ResearchProposalDraft
from atlas_eng.engine.domain.prompt_document import PromptDocument


class MockAIProvider(AIProvider):
    """Deterministic mock provider for unit testing."""

    def __init__(self, stubbed_response: str) -> None:
        self.stubbed_response = stubbed_response

    def generate(self, _request: AIRequest) -> AIResponse:
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
        prompt=PromptDocument(system_prompt="System", context="", task="Hi"),
        context=ContextPayload(serialized_context=""),
    )
    resp = provider.generate(request)
    assert resp.content == "Mocked Output"


def test_gemini_provider() -> None:
    provider = GeminiAIProvider()
    assert provider.capabilities().context_window > 0


def test_flatten_schema_is_a_noop_without_defs() -> None:
    schema = {"type": "object", "properties": {"a": {"type": "string"}}}
    assert _flatten_schema(schema) == schema


def test_flatten_schema_resolves_nested_refs() -> None:
    """Every non-trivial proposal draft (e.g. ResearchProposalDraft, which
    nests ResearchFindingDraft/ResearchEvidenceDraft) produces $defs/$ref
    via model_json_schema() -- Gemini must receive it fully inlined."""
    schema = ResearchProposalDraft.model_json_schema()
    assert "$defs" in schema  # sanity check: this schema does nest submodels

    flattened = _flatten_schema(schema)

    assert "$defs" not in flattened
    assert _no_refs_remain(flattened)


def _no_refs_remain(node: object) -> bool:
    if isinstance(node, dict):
        if "$ref" in node:
            return False
        return all(_no_refs_remain(value) for value in node.values())
    if isinstance(node, list):
        return all(_no_refs_remain(item) for item in node)
    return True


def test_gemini_without_its_extra_explains_how_to_install(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``google-genai`` is optional; a missing install must say what to run."""
    from atlas_eng.engine.ai.adapters.gemini import (  # noqa: PLC0415
        GeminiEmbeddingProvider,
    )
    from atlas_eng.engine.ai.config import ProviderConfig  # noqa: PLC0415
    from atlas_eng.engine.ai.exceptions import AIProviderException  # noqa: PLC0415
    from atlas_eng.engine.config import Settings  # noqa: PLC0415

    # A None entry in sys.modules makes the import raise ImportError.
    monkeypatch.setitem(sys.modules, "google.genai", None)
    settings = Settings(gemini_api_key="key", gemini_model="model")
    config = ProviderConfig(protocol="GEMINI", api_key="key", model="model")
    request = AIRequest(
        prompt=PromptDocument(system_prompt="s", context="", task="t"),
        context=ContextPayload(serialized_context=""),
    )

    with pytest.raises(AIProviderException, match=r"atlas-eng\[gemini\]"):
        GeminiAIProvider(config, settings).generate(request)
    with pytest.raises(AIProviderException, match=r"atlas-eng\[gemini\]"):
        GeminiEmbeddingProvider(config, settings).embed(["text"])
