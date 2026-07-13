"""Prompt template abstractions and core implementations."""

from abc import ABC, abstractmethod
from typing import Any

from engine.domain.ai import ContextPayload, PromptTemplateMetadata
from engine.domain.enums import ProposalType


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
    def build(self, context: ContextPayload, user_instructions: str = "") -> str:
        """Assemble the complete prompt payload.

        Args:
            context: The immutable domain context frozen for this generation.
            user_instructions: Optional specific directions from the user.

        Returns:
            The raw text prompt to be submitted to the AIProvider.
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
        # Placeholder for actual Research draft schema
        return {"type": "object", "properties": {"research_synthesis": {"type": "string"}}}

    def build(self, context: ContextPayload, user_instructions: str = "") -> str:
        return (
            "You are acting as a Principal Engineer doing Research.\n"
            f"Context: {context.serialized_context}\n"
            f"Instructions: {user_instructions}\n"
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
        return {"type": "object", "properties": {"planning_tasks": {"type": "array"}}}

    def build(self, context: ContextPayload, user_instructions: str = "") -> str:
        return (
            "You are acting as a Principal Engineer writing a Plan.\n"
            f"Context: {context.serialized_context}\n"
            f"Instructions: {user_instructions}\n"
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
        return {"type": "object", "properties": {"components": {"type": "array"}}}

    def build(self, context: ContextPayload, user_instructions: str = "") -> str:
        return (
            "You are acting as a Principal Engineer defining Architecture.\n"
            f"Context: {context.serialized_context}\n"
            f"Instructions: {user_instructions}\n"
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
        return {"type": "object", "properties": {"findings": {"type": "array"}}}

    def build(self, context: ContextPayload, user_instructions: str = "") -> str:
        return (
            "You are acting as a Principal Engineer evaluating design against constraints.\n"
            f"Context: {context.serialized_context}\n"
            f"Instructions: {user_instructions}\n"
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

    def build(self, context: ContextPayload, user_instructions: str = "") -> str:
        return (
            "Summarize the provided context into an engineering memory.\n"
            f"Context: {context.serialized_context}\n"
            f"Instructions: {user_instructions}\n"
        )
