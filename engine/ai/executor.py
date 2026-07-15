"""Provider-independent runtime for executing typed prompt drafts."""

import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from engine.ai.context import ContextStrategy
from engine.ai.exceptions import InvalidProposalException
from engine.ai.prompts import PromptTemplate
from engine.ai.provider import AIProvider
from engine.domain.ai import AIGenerationParameters, AIRequest, ContextPayload

T = TypeVar("T", bound=BaseModel)


class PromptExecutor:
    """Execute a template and return a validated draft, never a proposal."""

    def __init__(self, provider: AIProvider, context_strategy: ContextStrategy) -> None:
        self._provider = provider
        self._context_strategy = context_strategy

    def execute(
        self,
        template: PromptTemplate,
        raw_context: ContextPayload,
        draft_cls: type[T],
        user_instructions: str = "",
        parameters: AIGenerationParameters | None = None,
    ) -> T:
        """Apply context, invoke the provider, and validate its JSON response."""
        context = self._context_strategy.apply(raw_context)
        request = AIRequest(
            prompt=template.build(context, user_instructions),
            context=context,
            tools=[],
            response_schema=template.expected_schema,
            parameters=parameters or AIGenerationParameters(),
        )
        response = self._provider.generate(request)
        try:
            return draft_cls.model_validate(json.loads(response.content))
        except (json.JSONDecodeError, ValidationError) as error:
            raise InvalidProposalException(
                f"Failed to parse generation into {draft_cls.__name__}: {error}"
            ) from error
