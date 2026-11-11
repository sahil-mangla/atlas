"""Adapter for Ollama's local generation protocol."""

from collections.abc import Sequence
from typing import Any

from langfuse.decorators import langfuse_context, observe

from engine.ai.adapters._http import parse_embeddings, post_json
from engine.ai.config import ProviderConfig
from engine.ai.embeddings import EmbeddingProvider
from engine.ai.exceptions import AIProviderException
from engine.ai.provider import AIProvider
from engine.domain.ai import AIRequest, AIResponse, ProviderCapabilities


class OllamaAIProvider(AIProvider):
    """Execute the same normalized requests against a local Ollama server."""

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config

    @observe(
        as_type="generation",
        name="ollama_generate",
        capture_input=False,
        capture_output=False,
    )
    def generate(self, request: AIRequest) -> AIResponse:
        if not self._config.model:
            raise AIProviderException("Ollama protocol requires a model.")
        endpoint = (self._config.endpoint or "http://localhost:11434").rstrip("/")
        options: dict[str, Any] = request.parameters.model_dump(exclude_none=True)
        if request.parameters.max_output_tokens is not None:
            options["num_predict"] = options.pop("max_output_tokens")
        payload: dict[str, Any] = {
            "model": self._config.model,
            "prompt": request.prompt.user_prompt,
            "system": request.prompt.system_prompt,
            "stream": False,
            "options": options,
        }
        if request.response_schema is not None:
            # Ollama's /api/generate accepts a full JSON schema object here,
            # not just the string "json" -- passing the schema constrains
            # the model to that shape instead of merely valid JSON,
            # honoring the structured_output capability this adapter
            # declares below.
            payload["format"] = request.response_schema
        payload.update(self._config.options)
        data = post_json(
            endpoint + "/api/generate",
            payload,
            {},
            timeout=self._config.timeout_seconds,
        )

        content_str = str(data.get("response", ""))
        prompt_tokens = int(data.get("prompt_eval_count", 0))
        completion_tokens = int(data.get("eval_count", 0))

        langfuse_context.update_current_observation(
            model=self._config.model,
            input=[
                {"role": "system", "content": request.prompt.system_prompt},
                {"role": "user", "content": request.prompt.user_prompt},
            ],
            output=content_str,
            usage={"input": prompt_tokens, "output": completion_tokens},
        )

        return AIResponse(
            content=content_str,
            usage_metrics={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            },
            finish_reason=str(data.get("done_reason", "unknown")),
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            structured_output=True,
            streaming_support=False,
            tool_calling=False,
            image_input=False,
            reasoning_support=False,
            context_window=int(self._config.options.get("context_window", 32768)),
        )


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Embeddings from a local Ollama server (``/api/embed``)."""

    def __init__(self, config: ProviderConfig) -> None:
        if not config.model:
            raise AIProviderException(
                "Ollama embeddings require ATLAS_EMBEDDING_MODEL "
                "(for example nomic-embed-text)."
            )
        self._config = config

    @property
    def model_id(self) -> str:
        return f"OLLAMA:{self._config.model}"

    @observe(name="ollama_embed", capture_input=False, capture_output=False)
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        endpoint = (self._config.endpoint or "http://localhost:11434").rstrip("/")
        data = post_json(
            endpoint + "/api/embed",
            {"model": self._config.model, "input": list(texts)},
            {},
            timeout=self._config.timeout_seconds,
        )
        return parse_embeddings(data.get("embeddings"), len(texts))
