"""AI domain models and abstract orchestrator contracts."""

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from engine.domain.enums import ProposalStatus, ProposalType
from engine.domain.prompt_document import PromptDocument


class AIToolSchema(BaseModel):
    """Formal schema defining a tool available to the provider."""

    name: str = Field(description="Name of the tool.")
    description: str = Field(description="Description of what the tool does.")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="JSON schema for the parameters."
    )


class AIGenerationParameters(BaseModel):
    """Configuration for LLM generation parameters."""

    temperature: float | None = Field(
        default=None, description="Generation temperature."
    )
    top_p: float | None = Field(
        default=None, description="Nucleus sampling probability."
    )
    max_output_tokens: int | None = Field(
        default=None, description="Max generated tokens."
    )


class ProviderCapabilities(BaseModel):
    """Capabilities supported by the specific AI Provider implementation."""

    structured_output: bool = Field(description="Can enforce JSON schema output.")
    streaming_support: bool = Field(description="Supports streaming responses.")
    tool_calling: bool = Field(description="Supports tool calling / function calling.")
    image_input: bool = Field(description="Supports multimodal image inputs.")
    reasoning_support: bool = Field(
        description="Exposes raw reasoning/scratchpad traces."
    )
    context_window: int = Field(description="Maximum context window size in tokens.")


class ContextPayload(BaseModel):
    """Immutable freeze of subsystem context and traceability metadata."""

    model_config = ConfigDict(frozen=True)

    planning_snapshot_id: UUID | None = Field(
        default=None, description="Approved planning snapshot."
    )
    research_snapshot_id: UUID | None = Field(
        default=None, description="Approved research snapshot."
    )
    architecture_snapshot_id: UUID | None = Field(
        default=None, description="Approved architecture snapshot."
    )
    evaluation_snapshot_id: UUID | None = Field(
        default=None, description="Approved evaluation snapshot."
    )
    memory_entries: tuple[UUID, ...] = Field(
        default_factory=tuple, description="Relevant memory entries."
    )
    knowledge_entry_ids: tuple[UUID, ...] = Field(
        default_factory=tuple, description="Relevant published engineering knowledge."
    )
    serialized_context: str = Field(
        description="Stringified context payload provided to LLM."
    )


class AIRequest(BaseModel):
    """Deterministic payload sent to the AI provider."""

    prompt: PromptDocument = Field(description="The structured prompt document.")
    context: ContextPayload = Field(description="Immutable snapshot context.")
    tools: list[AIToolSchema] = Field(
        default_factory=list, description="Tools available."
    )
    response_schema: dict[str, Any] | None = Field(
        default=None, description="Target JSON schema."
    )
    parameters: AIGenerationParameters = Field(default_factory=AIGenerationParameters)


class AIResponse(BaseModel):
    """Provider-agnostic normalized response from the AI."""

    content: str = Field(description="Generated string content.")
    usage_metrics: dict[str, int] = Field(
        default_factory=dict, description="Token usage stats."
    )
    finish_reason: str = Field(
        description="Reason for termination (e.g. stop, length)."
    )


class PromptTemplateMetadata(BaseModel):
    """Metadata describing a prompt template."""

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4, description="Unique template identifier.")
    version: int = Field(description="Version number of this prompt.")
    supported_subsystem: ProposalType = Field(
        description="Subsystem this prompt targets."
    )


class AIProposal[T](BaseModel):
    """Generic wrapper for LLM generated drafts."""

    id: UUID = Field(default_factory=uuid4, description="Unique proposal identifier.")
    proposal_type: ProposalType = Field(description="Target subsystem domain type.")
    status: ProposalStatus = Field(
        default=ProposalStatus.DRAFT, description="Current lifecycle state."
    )
    prompt_metadata: PromptTemplateMetadata = Field(
        description="Metadata of the prompt used."
    )
    context_used: ContextPayload = Field(description="The exact context snapshot used.")
    data: T = Field(
        description="The generic payload, typed to the target subsystem draft."
    )
    human_feedback: str | None = Field(
        default=None, description="Feedback from human review."
    )
