"""Gemini adapter implementation of the AIProvider.

Google SDK imports intentionally stay in this module so the rest of the
application remains provider independent.
"""

from collections.abc import Sequence
from typing import Any

from google import genai
from google.genai import types
from langfuse.decorators import langfuse_context, observe

from engine.ai.adapters._http import parse_embeddings
from engine.ai.config import ProviderConfig
from engine.ai.embeddings import EmbeddingProvider
from engine.ai.exceptions import AIProviderException
from engine.ai.provider import AIProvider
from engine.config import Settings, get_settings
from engine.domain.ai import AIRequest, AIResponse, ProviderCapabilities


def _inline_refs(node: Any, defs: dict[str, Any]) -> Any:
    if isinstance(node, dict):
        if "$ref" in node:
            ref_name = node["$ref"].rsplit("/", 1)[-1]
            return _inline_refs(defs[ref_name], defs)
        return {
            key: _inline_refs(value, defs)
            for key, value in node.items()
            if key != "$defs"
        }
    if isinstance(node, list):
        return [_inline_refs(item, defs) for item in node]
    return node


def _flatten_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Resolve Pydantic's $defs/$ref indirection before sending a schema to
    Gemini.

    Every non-trivial proposal draft (e.g. ResearchProposalDraft, which
    nests ResearchFindingDraft/ResearchEvidenceDraft) produces
    $defs/$ref via model_json_schema(). Passing that structure through
    unresolved risks Gemini failing or silently ignoring the schema on the
    default provider for exactly the drafts that matter most.
    """
    defs = schema.get("$defs", {})
    if not defs:
        return schema
    flattened: dict[str, Any] = _inline_refs(schema, defs)
    return flattened


class GeminiAIProvider(AIProvider):
    """Adapter bridging ATLAS AIProvider protocol with Google's Gemini SDK."""

    def __init__(
        self,
        config: ProviderConfig | Settings | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Initialize the adapter from injected application settings."""
        legacy_settings = config if isinstance(config, Settings) else None
        configured = settings or legacy_settings or get_settings()
        protocol_config = config if isinstance(config, ProviderConfig) else None
        self._api_key = (
            protocol_config.api_key if protocol_config else None
        ) or configured.gemini_api_key
        self._model = (
            protocol_config.model if protocol_config else None
        ) or configured.gemini_model

    @observe(
        as_type="generation",
        name="gemini_generate",
        capture_input=False,
        capture_output=False,
    )
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
                config_values["response_schema"] = _flatten_schema(
                    request.response_schema
                )
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

            prompt_tokens = (
                getattr(response.usage_metadata, "prompt_token_count", 0) or 0
            )
            completion_tokens = (
                getattr(response.usage_metadata, "candidates_token_count", 0) or 0
            )

            langfuse_context.update_current_observation(
                model=self._model,
                input=[
                    {"role": "system", "content": request.prompt.system_prompt},
                    {"role": "user", "content": request.prompt.user_prompt},
                ],
                output=response.text or "",
                usage={"input": prompt_tokens, "output": completion_tokens},
            )

            return AIResponse(
                content=response.text or "",
                usage_metrics={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
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
        """Describe capabilities implemented by this adapter today."""
        return ProviderCapabilities(
            structured_output=True,
            streaming_support=False,
            tool_calling=False,
            image_input=False,
            reasoning_support=False,
            context_window=2_000_000,
        )


DEFAULT_GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Embeddings via the Gemini SDK (SDK imports stay in this module)."""

    def __init__(
        self,
        config: ProviderConfig | None = None,
        settings: Settings | None = None,
    ) -> None:
        configured = settings or get_settings()
        self._api_key = (
            config.api_key if config else None
        ) or configured.gemini_api_key
        self._model = (
            config.model if config else None
        ) or DEFAULT_GEMINI_EMBEDDING_MODEL

    @property
    def model_id(self) -> str:
        return f"GEMINI:{self._model}"

    @observe(name="gemini_embed", capture_input=False, capture_output=False)
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not self._api_key:
            raise AIProviderException(
                "Gemini embeddings require ATLAS_GEMINI_API_KEY "
                "(or ATLAS_EMBEDDING_API_KEY)."
            )
        try:
            client = genai.Client(api_key=self._api_key)
            response = client.models.embed_content(
                model=self._model, contents=list(texts)
            )
        except Exception as error:
            raise AIProviderException(f"Gemini embedding error: {error}") from error
        return parse_embeddings(
            [list(item.values or []) for item in response.embeddings or []],
            len(texts),
        )
