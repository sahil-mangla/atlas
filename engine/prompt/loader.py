"""Prompt Loader for initializing and registering prompt templates."""

from pydantic import BaseModel

from engine.domain.ai_drafts import (
    ArchitectureProposalDraft,
    EvaluationProposalDraft,
    PlanningProposalDraft,
    ResearchProposalDraft,
)
from engine.prompt.registry import PromptRegistry
from engine.prompt.templates import (
    ArchitecturePromptTemplate,
    EvaluationPromptTemplate,
    PlanningPromptTemplate,
    PromptTemplate,
    ResearchPromptTemplate,
)


class PromptLoader:
    """Explicitly instantiates and registers prompt templates."""

    @staticmethod
    def load_registry() -> PromptRegistry:
        """Construct prompt templates and return an immutable registry."""
        templates: dict[type[BaseModel], PromptTemplate] = {
            ResearchProposalDraft: ResearchPromptTemplate(),
            PlanningProposalDraft: PlanningPromptTemplate(),
            ArchitectureProposalDraft: ArchitecturePromptTemplate(),
            EvaluationProposalDraft: EvaluationPromptTemplate(),
        }
        return PromptRegistry(templates)
