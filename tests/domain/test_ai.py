from uuid import UUID

from engine.domain.ai import (
    AIProposal,
    AIRequest,
    AIResponse,
    AIToolSchema,
    ContextPayload,
    PromptTemplateMetadata,
)
from engine.domain.enums import ProposalStatus, ProposalType


def test_ai_tool_schema() -> None:
    schema = AIToolSchema(name="search", description="Search tool", parameters={"type": "object"})
    assert schema.name == "search"
    assert schema.description == "Search tool"


def test_ai_request_response() -> None:
    context = ContextPayload(serialized_context="abc")
    request = AIRequest(
        prompt="hello",
        context=context,
        response_schema={"type": "string"},
    )
    assert request.prompt == "hello"

    response = AIResponse(content="world", finish_reason="stop")
    assert response.content == "world"


def test_ai_proposal() -> None:
    meta = PromptTemplateMetadata(version=1, supported_subsystem=ProposalType.RESEARCH)
    context = ContextPayload(serialized_context="data")
    proposal = AIProposal[dict[str, str]](
        proposal_type=ProposalType.RESEARCH,
        status=ProposalStatus.DRAFT,
        prompt_metadata=meta,
        context_used=context,
        data={"key": "value"},
    )
    assert isinstance(proposal.id, UUID)
    assert proposal.data["key"] == "value"
    assert proposal.status == ProposalStatus.DRAFT
