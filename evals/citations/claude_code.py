"""Eval-only AI provider that runs requests through Claude Code's print mode.

This lets the citation eval measure a frontier Claude model using the
operator's own Claude Code login, without an API key. It is deliberately not
part of the ``atlas_eng`` package: ATLAS users should use the ``ANTHROPIC``
protocol with an API key.

Each request runs ``claude -p`` with every tool disabled (so no web search:
citations come from the model's own knowledge), ATLAS's prompt as the whole
system prompt, no user settings, hooks or MCP servers, no saved session, and
from an empty directory so no CLAUDE.md is read. The prompt goes in on stdin.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from atlas_eng.engine.ai.adapters.anthropic import to_structured_output_schema
from atlas_eng.engine.ai.exceptions import AIProviderException
from atlas_eng.engine.ai.provider import AIProvider
from atlas_eng.engine.domain.ai import AIRequest, AIResponse, ProviderCapabilities

_DEFAULT_TIMEOUT_S = 900


class ClaudeCodeProvider(AIProvider):
    """Runs one ``claude -p`` process per request."""

    def __init__(self, model: str, timeout_s: int = _DEFAULT_TIMEOUT_S) -> None:
        executable = shutil.which("claude")
        if executable is None:
            raise AIProviderException("The `claude` command is not installed.")
        self._executable = executable
        self._model = model
        self._timeout_s = timeout_s
        self._workdir = Path(tempfile.mkdtemp(prefix="atlas-claude-code-"))
        #: API-equivalent cost of every call so far, as Claude Code reports it.
        self.cost_usd = 0.0
        #: Model ids Claude Code reported using, with their token counts.
        self.model_usage: dict[str, dict[str, int]] = {}

    def _command(self, system_prompt: str, schema: dict[str, Any] | None) -> list[str]:
        command = [
            self._executable,
            "-p",
            "--output-format",
            "json",
            "--model",
            self._model,
            "--tools",
            "",
            "--system-prompt",
            system_prompt,
            "--setting-sources",
            "",
            "--strict-mcp-config",
            "--no-session-persistence",
        ]
        if schema is not None:
            command += [
                "--json-schema",
                json.dumps(to_structured_output_schema(schema)),
            ]
        return command

    def run(
        self, system_prompt: str, user_prompt: str, schema: dict[str, Any] | None
    ) -> tuple[str, dict[str, Any]]:
        """Send one prompt.

        Returns the text (JSON when a schema is given) and the raw reply.
        """
        try:
            completed = subprocess.run(
                self._command(system_prompt, schema),
                input=user_prompt,
                capture_output=True,
                text=True,
                cwd=self._workdir,
                timeout=self._timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise AIProviderException(
                f"claude -p timed out after {self._timeout_s}s"
            ) from error
        try:
            reply: dict[str, Any] = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise AIProviderException(
                f"claude -p returned no JSON (exit {completed.returncode}): "
                f"{(completed.stderr or completed.stdout)[:300]}"
            ) from error
        if reply.get("is_error") or reply.get("subtype") != "success":
            raise AIProviderException(
                f"claude -p failed ({reply.get('subtype')}): "
                f"{str(reply.get('result'))[:300]}"
            )
        self.cost_usd += float(reply.get("total_cost_usd") or 0.0)
        for model_id, usage in (reply.get("modelUsage") or {}).items():
            totals = self.model_usage.setdefault(model_id, {"input": 0, "output": 0})
            totals["input"] += (
                int(usage.get("inputTokens", 0))
                + int(usage.get("cacheReadInputTokens", 0))
                + int(usage.get("cacheCreationInputTokens", 0))
            )
            totals["output"] += int(usage.get("outputTokens", 0))
        if schema is not None and reply.get("structured_output") is not None:
            return json.dumps(reply["structured_output"]), reply
        return str(reply.get("result", "")), reply

    def generate(self, request: AIRequest) -> AIResponse:
        content, reply = self.run(
            request.prompt.system_prompt,
            request.prompt.user_prompt,
            request.response_schema,
        )
        usage = reply.get("usage") or {}
        prompt_tokens = (
            int(usage.get("input_tokens", 0))
            + int(usage.get("cache_creation_input_tokens", 0))
            + int(usage.get("cache_read_input_tokens", 0))
        )
        return AIResponse(
            content=content,
            usage_metrics={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": int(usage.get("output_tokens", 0)),
            },
            finish_reason=str(reply.get("stop_reason") or "stop"),
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            structured_output=True,
            streaming_support=False,
            tool_calling=False,
            image_input=False,
            reasoning_support=False,
            context_window=1_000_000,
        )
