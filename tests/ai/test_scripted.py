"""The offline SCRIPTED protocol: canned drafts, fault modes, embeddings."""

import json
import math

import pytest
from pydantic import BaseModel

from atlas_eng.engine.ai.adapters.scripted import (
    FAULT_MALFORMED_JSON,
    FAULT_PROVIDER_ERROR,
    FAULT_SCHEMA_VIOLATION,
    FAULT_TRUNCATED,
    ScriptedAIProvider,
    ScriptedEmbeddingProvider,
)
from atlas_eng.engine.ai.config import ProviderConfig
from atlas_eng.engine.ai.context import IdentityContextStrategy
from atlas_eng.engine.ai.embedding_factory import EmbeddingFactory
from atlas_eng.engine.ai.engineering_services import (
    ArchitectureProposalValidator,
    EvaluationProposalValidator,
    PlanningProposalValidator,
    ResearchProposalValidator,
)
from atlas_eng.engine.ai.exceptions import AIProviderException, InvalidProposalException
from atlas_eng.engine.ai.executor import PromptExecutor
from atlas_eng.engine.ai.factory import ProtocolFactory
from atlas_eng.engine.ai.observability import label_provider
from atlas_eng.engine.domain.ai import AIRequest, ContextPayload
from atlas_eng.engine.domain.ai_drafts import (
    ArchitectureProposalDraft,
    EvaluationProposalDraft,
    EvidenceSummaryBatchDraft,
    PlanningProposalDraft,
    ResearchProposalDraft,
)
from atlas_eng.engine.domain.prompt_document import PromptDocument
from atlas_eng.engine.prompt.loader import PromptLoader

_REGISTRY = PromptLoader.load_registry()
_DRAFT_TYPES = sorted(_REGISTRY._templates, key=lambda cls: cls.__name__)


def _execute[T: BaseModel](
    draft_cls: type[T], context: str = "", model: str | None = None
) -> T:
    provider = ScriptedAIProvider(ProviderConfig(protocol="SCRIPTED", model=model))
    executor = PromptExecutor(provider, IdentityContextStrategy())
    return executor.execute(
        _REGISTRY.resolve(draft_cls),
        ContextPayload(serialized_context=context),
        draft_cls,
    )


@pytest.mark.parametrize("draft_cls", _DRAFT_TYPES, ids=lambda cls: cls.__name__)
def test_every_registered_template_has_a_valid_scripted_draft(
    draft_cls: type[BaseModel],
) -> None:
    """A new prompt template without a script would break offline mode."""
    assert isinstance(_execute(draft_cls), draft_cls)


def test_scripted_drafts_pass_the_semantic_validators() -> None:
    ResearchProposalValidator().validate(_execute(ResearchProposalDraft))
    PlanningProposalValidator().validate(_execute(PlanningProposalDraft))
    ArchitectureProposalValidator().validate(_execute(ArchitectureProposalDraft))
    EvaluationProposalValidator().validate(_execute(EvaluationProposalDraft))


def test_research_draft_echoes_grounded_evidence_and_cites_it() -> None:
    evidence = [
        {
            "title": "A real paper",
            "type": "paper",
            "origin": "arxiv: https://example.org/1",
            "citation": "Someone (2024). A real paper.",
            "summary": "s",
            "external_id": "arxiv:1",
        }
    ]
    context = (
        "project context\n\nGROUNDED EVIDENCE (reproduce exactly in your "
        f"`evidence` array, including `external_id`, do not alter):\n"
        f"{json.dumps(evidence, indent=2)}"
    )

    draft = _execute(ResearchProposalDraft, context)

    assert [item.model_dump() for item in draft.evidence] == evidence
    assert draft.findings[0].evidence_indices == [0]
    assert draft.opportunities
    ResearchProposalValidator().validate(draft)


def test_research_draft_without_evidence_invents_none() -> None:
    draft = _execute(ResearchProposalDraft)

    assert draft.evidence == []
    assert draft.findings == []
    assert draft.opportunities == []


def test_evidence_summaries_match_the_number_of_candidates() -> None:
    context = "[0] First\nabstract\n\n[1] Second\nabstract\n\n[2] Third\nabstract"

    assert len(_execute(EvidenceSummaryBatchDraft, context).summaries) == 3


def test_output_is_deterministic() -> None:
    assert _execute(PlanningProposalDraft) == _execute(PlanningProposalDraft)


@pytest.mark.parametrize(
    "fault", [FAULT_MALFORMED_JSON, FAULT_SCHEMA_VIOLATION, FAULT_TRUNCATED]
)
def test_bad_output_faults_surface_as_invalid_proposals(fault: str) -> None:
    with pytest.raises(InvalidProposalException):
        _execute(PlanningProposalDraft, model=fault)


def test_provider_error_fault_raises_provider_exception() -> None:
    with pytest.raises(AIProviderException):
        _execute(PlanningProposalDraft, model=FAULT_PROVIDER_ERROR)


def test_unknown_schema_is_an_explicit_error() -> None:
    request = AIRequest(
        prompt=PromptDocument(system_prompt="s", context="", task="t"),
        context=ContextPayload(serialized_context=""),
        response_schema={"title": "SomethingNew"},
    )

    with pytest.raises(AIProviderException, match="SomethingNew"):
        ScriptedAIProvider().generate(request)


def test_stubbed_response_overrides_the_script() -> None:
    provider = ScriptedAIProvider(stubbed_response='{"summary": "x"}')
    request = AIRequest(
        prompt=PromptDocument(system_prompt="s", context="", task="t"),
        context=ContextPayload(serialized_context=""),
    )

    response = provider.generate(request)

    assert response.content == '{"summary": "x"}'
    assert response.usage_metrics["prompt_tokens"] > 0


def test_factories_resolve_the_scripted_protocol() -> None:
    config = ProviderConfig(protocol="scripted")

    provider = ProtocolFactory().resolve(config)

    assert isinstance(provider, ScriptedAIProvider)
    assert label_provider(provider) == "scripted"
    assert isinstance(EmbeddingFactory().resolve(config), ScriptedEmbeddingProvider)


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def test_scripted_embeddings_are_deterministic_unit_vectors() -> None:
    embedder = ScriptedEmbeddingProvider()

    first, again, empty = embedder.embed(["rollback plan", "rollback plan", ""])

    assert first == again
    assert math.isclose(math.sqrt(sum(v * v for v in first)), 1.0)
    assert math.isclose(math.sqrt(sum(v * v for v in empty)), 1.0)


def test_scripted_embeddings_rank_shared_words_closer() -> None:
    embedder = ScriptedEmbeddingProvider()

    query, related, unrelated = embedder.embed(
        [
            "database rollback strategy",
            "rollback strategy for the database",
            "frontend colour palette",
        ]
    )

    assert _cosine(query, related) > _cosine(query, unrelated)
