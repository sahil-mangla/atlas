"""Protocol-independent configuration for the AI runtime."""

from typing import Any

from pydantic import AliasChoices, BaseModel, Field, field_validator


class ProviderConfig(BaseModel):
    """Configuration used to resolve and configure one AI protocol adapter.

    ``provider_name``, ``model_name``, and ``endpoint_url`` remain accepted as
    input aliases for compatibility with the pre-protocol runtime.
    """

    protocol: str = Field(
        default="GEMINI",
        validation_alias=AliasChoices("protocol", "provider_name"),
        description=(
            "Registered protocol name, for example GEMINI or OPENAI_COMPATIBLE."
        ),
    )
    endpoint: str | None = Field(
        default=None,
        validation_alias=AliasChoices("endpoint", "endpoint_url", "base_url"),
        description="Protocol endpoint or base URL.",
    )
    model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("model", "model_name"),
        description="Model identifier understood by the selected protocol.",
    )
    api_key: str | None = Field(default=None, description="Protocol credential.")
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Protocol-specific runtime options.",
    )

    @field_validator("protocol")
    @classmethod
    def validate_protocol(cls, value: str) -> str:
        """Reject empty protocol identifiers before adapter construction."""
        if not value.strip():
            raise ValueError("protocol must not be empty")
        return value.upper()

    @property
    def provider_name(self) -> str:
        """Legacy name for :attr:`protocol`."""
        return self.protocol

    @property
    def model_name(self) -> str | None:
        """Legacy name for :attr:`model`."""
        return self.model

    @property
    def endpoint_url(self) -> str | None:
        """Legacy name for :attr:`endpoint`."""
        return self.endpoint
