"""Immutable registry for prompt templates."""

from collections.abc import Mapping
from types import MappingProxyType

from pydantic import BaseModel

from engine.prompt.templates import PromptTemplate


class PromptRegistry:
    """Resolve templates by the draft schema they are expected to produce."""

    def __init__(self, templates: Mapping[type[BaseModel], PromptTemplate]) -> None:
        self._templates = MappingProxyType(dict(templates))

    def resolve(self, draft_cls: type[BaseModel]) -> PromptTemplate:
        """Return the template registered for ``draft_cls``.

        Raises:
            KeyError: If no template is registered for the requested draft type.
        """
        try:
            return self._templates[draft_cls]
        except KeyError as error:
            raise KeyError(
                f"No prompt template registered for {draft_cls.__name__}."
            ) from error
