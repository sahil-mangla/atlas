from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from engine.domain.ai import (
    AIProposal,
    AIRequest,
    AIResponse,
    AIToolSchema,
    ContextPayload,
    PromptTemplateMetadata,
)
from engine.domain.enums import ProposalStatus, ProposalType
from engine.domain.prompt_document import PromptDocument


def test_ai_tool_schema() -> None:
    schema = AIToolSchema(
        name="search", description="Search tool", parameters={"type": "object"}
    )
    assert schema.name == "search"
    assert schema.description == "Search tool"


def test_ai_request_response() -> None:
    context = ContextPayload(serialized_context="abc")
    request = AIRequest(
        prompt=PromptDocument(system_prompt="System", context="abc", task="hello"),
        context=context,
        response_schema={"type": "string"},
    )
    assert request.prompt.task == "hello"

    response = AIResponse(content="world", finish_reason="stop")
    assert response.content == "world"


def test_context_payload_is_immutable() -> None:
    context = ContextPayload(serialized_context="abc")

    with pytest.raises(ValidationError):
        context.serialized_context = "changed"

    with pytest.raises(ValidationError):
        context.knowledge_entry_ids += (uuid4(),)


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
