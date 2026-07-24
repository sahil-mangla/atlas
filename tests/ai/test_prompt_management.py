"""Behavioral tests for the Prompt Management layer."""

import pytest
from pydantic import ValidationError

from engine.domain.ai_drafts import (
    ArchitectureProposalDraft,
    EvaluationProposalDraft,
    PlanningProposalDraft,
    ResearchProposalDraft,
    SummaryDraft,
)
from engine.prompt.loader import PromptLoader
from engine.prompt.templates import (
    ArchitecturePromptTemplate,
    EvaluationPromptTemplate,
    PlanningPromptTemplate,
    ResearchPromptTemplate,
    SummaryPromptTemplate,
)


def test_prompt_loader_registers_the_same_template_set_deterministically() -> None:
    first_registry = PromptLoader.load_registry()
    second_registry = PromptLoader.load_registry()

    assert isinstance(
        first_registry.resolve(ResearchProposalDraft), ResearchPromptTemplate
    )
    assert isinstance(
        first_registry.resolve(PlanningProposalDraft), PlanningPromptTemplate
    )
    assert isinstance(
        first_registry.resolve(ArchitectureProposalDraft), ArchitecturePromptTemplate
    )
    assert isinstance(
        first_registry.resolve(EvaluationProposalDraft), EvaluationPromptTemplate
    )
    assert type(first_registry.resolve(ResearchProposalDraft)) is type(
        second_registry.resolve(ResearchProposalDraft)
    )
    assert isinstance(first_registry.resolve(SummaryDraft), SummaryPromptTemplate)


def test_registered_prompt_definitions_and_metadata_are_immutable() -> None:
    registry = PromptLoader.load_registry()
    template = registry.resolve(ResearchProposalDraft)

    with pytest.raises(TypeError):
        registry._templates[ResearchProposalDraft] = template  # type: ignore[index]
    with pytest.raises(AttributeError, match="immutable"):
        template._metadata = template.metadata
    with pytest.raises(ValidationError):
        template.metadata.version = 2
