"""Gemini adapter implementation of the AIProvider.

Google SDK imports intentionally stay in this module so the rest of the
application remains provider independent.
"""

from typing import Any

from google import genai
from google.genai import types

from engine.ai.exceptions import AIProviderException
from engine.ai.provider import AIProvider
from engine.config import Settings, get_settings
from engine.domain.ai import AIRequest, AIResponse, ProviderCapabilities


class GeminiAIProvider(AIProvider):
    """Adapter bridging ATLAS AIProvider protocol with Google's Gemini SDK."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the adapter from injected application settings."""
        configured = settings or get_settings()
        self._api_key = configured.gemini_api_key
        self._model = configured.gemini_model

    def generate(self, request: AIRequest) -> AIResponse:
        """Process an AIRequest via Gemini.

        Gemini-specific request and response types are constrained to this module.
        """
        if not self._api_key or not self._model:
            raise AIProviderException(
                "Gemini provider requires ATLAS_GEMINI_API_KEY and ATLAS_GEMINI_MODEL."
            )
        try:
            config_values: dict[str, Any] = {
                "system_instruction": request.prompt.system_prompt,
                "response_mime_type": "application/json",
            }
            if request.response_schema is not None:
                config_values["response_schema"] = request.response_schema
            if request.parameters.temperature is not None:
                config_values["temperature"] = request.parameters.temperature
            if request.parameters.top_p is not None:
                config_values["top_p"] = request.parameters.top_p
            if request.parameters.max_output_tokens is not None:
                config_values["max_output_tokens"] = (
                    request.parameters.max_output_tokens
                )

            client = genai.Client(api_key=self._api_key)
            response = client.models.generate_content(
                model=self._model,
                contents=request.prompt.user_prompt,
                config=types.GenerateContentConfig(**config_values),
            )
            return AIResponse(
                content=response.text or "",
                usage_metrics={
                    "prompt_tokens": getattr(
                        response.usage_metadata, "prompt_token_count", 0
                    )
                    or 0,
                    "completion_tokens": getattr(
                        response.usage_metadata, "candidates_token_count", 0
                    )
                    or 0,
                },
                finish_reason=(
                    str(response.candidates[0].finish_reason)
                    if response.candidates
                    else "unknown"
                ),
            )
        except Exception as error:
            raise AIProviderException(f"Gemini provider error: {error}") from error

    def capabilities(self) -> ProviderCapabilities:
        """Describe Gemini's capabilities."""
        return ProviderCapabilities(
            structured_output=True,
            streaming_support=True,
            tool_calling=True,
            image_input=True,
            reasoning_support=False,  # Update when applicable
            context_window=2_000_000,
        )
