"""Provider-independent structured prompt value objects."""

from pydantic import BaseModel, ConfigDict


class PromptDocument(BaseModel):
    """The deterministic parts of a prompt before provider rendering.

    Keeping these sections separate prevents provider-specific prompt formatting
    from leaking into templates or application services.
    """

    model_config = ConfigDict(frozen=True)

    system_prompt: str
    context: str
    task: str

    @property
    def user_prompt(self) -> str:
        """Render the provider-neutral user-facing portion of the prompt."""
        return f"## Engineering Context\n{self.context}\n\n## Task\n{self.task}"
