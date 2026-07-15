"""Prompt template abstractions and core implementations with real schemas."""

from abc import ABC, abstractmethod
from typing import Any

from engine.domain.ai import ContextPayload, PromptTemplateMetadata
from engine.domain.ai_drafts import (
    ArchitectureProposalDraft,
    EvaluationProposalDraft,
    PlanningProposalDraft,
    ResearchProposalDraft,
)
from engine.domain.enums import ProposalType
from engine.domain.prompt_document import PromptDocument


class PromptTemplate(ABC):
    """Abstract template definition for generating LLM prompts."""

    @property
    @abstractmethod
    def metadata(self) -> PromptTemplateMetadata:
        """Expose the metadata including version and supported subsystem."""
        pass

    @property
    @abstractmethod
    def expected_schema(self) -> dict[str, Any] | None:
        """The formal JSON schema this template expects the LLM to output."""
        pass

    @abstractmethod
    def build(
        self, context: ContextPayload, user_instructions: str = ""
    ) -> PromptDocument:
        """Assemble the complete prompt payload.

        Args:
            context: The immutable domain context frozen for this generation.
            user_instructions: Optional specific directions from the user.

        Returns:
            A structured, provider-independent prompt document.
        """
        pass


class ResearchPromptTemplate(PromptTemplate):
    """Template for generating Research proposals."""

    def __init__(self) -> None:
        self._metadata = PromptTemplateMetadata(
            version=1,
            supported_subsystem=ProposalType.RESEARCH,
        )

    @property
    def metadata(self) -> PromptTemplateMetadata:
        return self._metadata

    @property
    def expected_schema(self) -> dict[str, Any] | None:
        return ResearchProposalDraft.model_json_schema()

    def build(
        self, context: ContextPayload, user_instructions: str = ""
    ) -> PromptDocument:
        return PromptDocument(
            system_prompt=(
                "You are a Principal Engineer producing a research proposal. "
                "Return only JSON that conforms to the supplied schema."
            ),
            context=context.serialized_context,
            task=(
                "Produce a research proposal using this JSON schema:\n"
                f"{self.expected_schema}\n\nUser instructions: {user_instructions}"
            ),
        )


class PlanningPromptTemplate(PromptTemplate):
    """Template for generating Planning proposals."""

    def __init__(self) -> None:
        self._metadata = PromptTemplateMetadata(
            version=1,
            supported_subsystem=ProposalType.PLANNING,
        )

    @property
    def metadata(self) -> PromptTemplateMetadata:
        return self._metadata

    @property
    def expected_schema(self) -> dict[str, Any] | None:
        return PlanningProposalDraft.model_json_schema()

    def build(
        self, context: ContextPayload, user_instructions: str = ""
    ) -> PromptDocument:
        return PromptDocument(
            system_prompt=(
                "You are a Principal Engineer producing an implementation plan. "
                "Return only JSON that conforms to the supplied schema."
            ),
            context=context.serialized_context,
            task=(
                "Produce a planning proposal using this JSON schema:\n"
                f"{self.expected_schema}\n\nUser instructions: {user_instructions}"
            ),
        )


class ArchitecturePromptTemplate(PromptTemplate):
    """Template for generating Architecture proposals."""

    def __init__(self) -> None:
        self._metadata = PromptTemplateMetadata(
            version=1,
            supported_subsystem=ProposalType.ARCHITECTURE,
        )

    @property
    def metadata(self) -> PromptTemplateMetadata:
        return self._metadata

    @property
    def expected_schema(self) -> dict[str, Any] | None:
        return ArchitectureProposalDraft.model_json_schema()

    def build(
        self, context: ContextPayload, user_instructions: str = ""
    ) -> PromptDocument:
        return PromptDocument(
            system_prompt=(
                "You are a Principal Engineer producing an architecture proposal. "
                "Return only JSON that conforms to the supplied schema."
            ),
            context=context.serialized_context,
            task=(
                "Produce an architecture proposal using this JSON schema:\n"
                f"{self.expected_schema}\n\nUser instructions: {user_instructions}"
            ),
        )


class EvaluationPromptTemplate(PromptTemplate):
    """Template for generating Evaluation proposals."""

    def __init__(self) -> None:
        self._metadata = PromptTemplateMetadata(
            version=1,
            supported_subsystem=ProposalType.EVALUATION,
        )

    @property
    def metadata(self) -> PromptTemplateMetadata:
        return self._metadata

    @property
    def expected_schema(self) -> dict[str, Any] | None:
        return EvaluationProposalDraft.model_json_schema()

    def build(
        self, context: ContextPayload, user_instructions: str = ""
    ) -> PromptDocument:
        return PromptDocument(
            system_prompt=(
                "You are a Principal Engineer evaluating engineering readiness. "
                "Return only JSON that conforms to the supplied schema."
            ),
            context=context.serialized_context,
            task=(
                "Produce an evaluation proposal using this JSON schema:\n"
                f"{self.expected_schema}\n\nUser instructions: {user_instructions}"
            ),
        )


class SummaryPromptTemplate(PromptTemplate):
    """Template for summarizing workflows or logs."""

    def __init__(self) -> None:
        self._metadata = PromptTemplateMetadata(
            version=1,
            supported_subsystem=ProposalType.MEMORY_CANDIDATE,
        )

    @property
    def metadata(self) -> PromptTemplateMetadata:
        return self._metadata

    @property
    def expected_schema(self) -> dict[str, Any] | None:
        return {"type": "object", "properties": {"summary": {"type": "string"}}}

    def build(
        self, context: ContextPayload, user_instructions: str = ""
    ) -> PromptDocument:
        return PromptDocument(
            system_prompt=(
                "Summarize engineering context. Return only JSON matching the schema."
            ),
            context=context.serialized_context,
            task=(
                f"Schema: {self.expected_schema}\n\n"
                f"User instructions: {user_instructions}"
            ),
        )
