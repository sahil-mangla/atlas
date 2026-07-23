"""Prompt template abstractions and core implementations with real schemas."""

from abc import ABC, abstractmethod
from typing import Any

from engine.domain.ai import ContextPayload, PromptTemplateMetadata
from engine.domain.ai_drafts import (
    ArchitectureProposalDraft,
    EvaluationProposalDraft,
    EvidenceSummaryBatchDraft,
    KnowledgeCandidateDraft,
    PlanningProposalDraft,
    ResearchProposalDraft,
)
from engine.domain.enums import ProposalType
from engine.domain.prompt_document import PromptDocument


class PromptTemplate(ABC):
    """Abstract template definition for generating LLM prompts."""

    def __setattr__(self, name: str, value: object) -> None:
        """Allow prompt-definition state to be assigned exactly once."""
        if name != "_metadata" or hasattr(self, name):
            raise AttributeError(
                "Prompt definitions are immutable after initialization."
            )
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        """Prevent deletion of immutable prompt-definition state."""
        raise AttributeError("Prompt definitions are immutable after initialization.")

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
                "Return only JSON that conforms to the supplied schema. "
                "All `*_indices` fields (evidence_indices, finding_indices) are "
                "0-based: the first item in a list is index 0, not 1. Every "
                "index you emit must be strictly less than the length of the "
                "list it references.\n\n"
                "You must never invent evidence. If the context below contains "
                "a 'GROUNDED EVIDENCE' section, your `evidence` array must "
                "reproduce exactly those entries, unchanged -- do not add, "
                "remove, reorder, or alter them, and do not append any "
                "additional entries. Build `findings`, `constraints`, and "
                "`opportunities` only by referencing that evidence via "
                "`evidence_indices`. If no 'GROUNDED EVIDENCE' section is "
                "present, leave `evidence` as an empty list rather than "
                "fabricating sources or citations."
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


class EvidenceSummaryPromptTemplate(PromptTemplate):
    """Condenses real, retrieved paper abstracts into plain-language summaries.

    Deliberately narrow -- unlike the proposal templates above, this one must
    never be asked to produce citations, titles, or origins: those come from
    the paper source's own API response (see ``engine.research.sources``)
    and are never passed through an LLM, so there is nothing for it to
    invent. Its only job is condensing text that already exists.
    """

    def __init__(self) -> None:
        self._metadata = PromptTemplateMetadata(
            version=1,
            supported_subsystem=ProposalType.EVIDENCE_SUMMARY,
        )

    @property
    def metadata(self) -> PromptTemplateMetadata:
        return self._metadata

    @property
    def expected_schema(self) -> dict[str, Any] | None:
        return EvidenceSummaryBatchDraft.model_json_schema()

    def build(
        self, context: ContextPayload, user_instructions: str = ""
    ) -> PromptDocument:
        return PromptDocument(
            system_prompt=(
                "You are condensing real paper abstracts for an engineering "
                "research review. Return only JSON conforming to the supplied "
                "schema. Summarize only what is stated in each abstract -- do "
                "not add claims, numbers, or conclusions the abstract does not "
                "contain. Produce exactly one summary per abstract, in the "
                "same order they are given, each 1-3 sentences focused on the "
                "engineering-relevant claim."
            ),
            context=context.serialized_context,
            task=(
                "Produce a summary batch using this JSON schema:\n"
                f"{self.expected_schema}\n\nUser instructions: {user_instructions}"
            ),
        )


class KnowledgeCandidatePromptTemplate(PromptTemplate):
    """Template for generating a new Knowledge Candidate."""

    def __init__(self) -> None:
        self._metadata = PromptTemplateMetadata(
            version=1,
            supported_subsystem=ProposalType.KNOWLEDGE_CANDIDATE,
        )

    @property
    def metadata(self) -> PromptTemplateMetadata:
        return self._metadata

    @property
    def expected_schema(self) -> dict[str, Any] | None:
        return KnowledgeCandidateDraft.model_json_schema()

    def build(
        self, context: ContextPayload, user_instructions: str = ""
    ) -> PromptDocument:
        return PromptDocument(
            system_prompt=(
                "You are an expert Engineering Knowledge Extractor.\n"
                "Your task is to identify and summarize key engineering "
                "principles, patterns, standards, or constraints from the "
                "provided context.\n"
                "Propose a formal Knowledge Candidate that captures this "
                "information. Return only JSON matching the schema."
            ),
            context=context.serialized_context,
            task=(
                f"Schema: {self.expected_schema}\n\n"
                f"User instructions: {user_instructions}"
            ),
        )
