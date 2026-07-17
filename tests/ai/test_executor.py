"""Focused tests for the provider-independent prompt execution runtime."""

from unittest.mock import Mock

import pytest

from engine.ai.context import ContextStrategy, IdentityContextStrategy
from engine.ai.exceptions import AIProviderException, InvalidProposalException
from engine.ai.executor import PromptExecutor
from engine.domain.ai import ContextPayload
from engine.domain.ai_drafts import ResearchProposalDraft
from engine.prompt.registry import PromptRegistry
from engine.prompt.templates import ResearchPromptTemplate
from tests.ai.test_adapters import MockAIProvider


def test_executor_invokes_provider_and_returns_typed_draft() -> None:
    provider = MockAIProvider('{"problem_statement": "Problem", "objectives": []}')
    executor = PromptExecutor(provider, IdentityContextStrategy())

    draft = executor.execute(
        ResearchPromptTemplate(),
        ContextPayload(serialized_context="context"),
        ResearchProposalDraft,
    )

    assert isinstance(draft, ResearchProposalDraft)
    assert draft.problem_statement == "Problem"


def test_executor_rejects_malformed_or_invalid_json() -> None:
    executor = PromptExecutor(MockAIProvider("not json"), IdentityContextStrategy())

    with pytest.raises(InvalidProposalException):
        executor.execute(
            ResearchPromptTemplate(),
            ContextPayload(serialized_context="context"),
            ResearchProposalDraft,
        )


def test_executor_propagates_provider_failure() -> None:
    provider = Mock()
    provider.generate.side_effect = AIProviderException("provider unavailable")
    executor = PromptExecutor(provider, IdentityContextStrategy())

    with pytest.raises(AIProviderException, match="provider unavailable"):
        executor.execute(
            ResearchPromptTemplate(),
            ContextPayload(serialized_context="context"),
            ResearchProposalDraft,
        )


def test_executor_applies_context_strategy() -> None:
    strategy = Mock(spec=ContextStrategy)
    context = ContextPayload(serialized_context="context")
    strategy.apply.return_value = context
    executor = PromptExecutor(
        MockAIProvider('{"problem_statement": "Problem", "objectives": []}'), strategy
    )

    executor.execute(ResearchPromptTemplate(), context, ResearchProposalDraft)

    strategy.apply.assert_called_once_with(context)


def test_registry_resolves_draft_and_cannot_be_mutated() -> None:
    template = ResearchPromptTemplate()
    registry = PromptRegistry({ResearchProposalDraft: template})

    assert registry.resolve(ResearchProposalDraft) is template
    with pytest.raises(KeyError):
        registry.resolve(Mock)
    with pytest.raises(TypeError):
        registry._templates[ResearchProposalDraft] = template  # type: ignore[index]
