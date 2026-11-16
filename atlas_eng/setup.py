"""First-run setup support: what each AI protocol needs, and checks on it.

Public SDK module used by ``atlas init`` and ``atlas doctor``. Clients get the
protocol requirements from here rather than from the engine, so the client
layer never imports engine internals.
"""

import importlib.util
import json
import os
import tempfile
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from dotenv import dotenv_values, find_dotenv

from atlas_eng.engine.ai.config import ProviderConfig
from atlas_eng.engine.ai.context import IdentityContextStrategy
from atlas_eng.engine.ai.embedding_factory import EmbeddingFactory
from atlas_eng.engine.ai.exceptions import AIException
from atlas_eng.engine.ai.executor import PromptExecutor
from atlas_eng.engine.ai.factory import ProtocolFactory
from atlas_eng.engine.config import Settings
from atlas_eng.engine.domain.ai import ContextPayload
from atlas_eng.engine.domain.ai_drafts import SummaryDraft
from atlas_eng.engine.prompt.templates import SummaryPromptTemplate


@dataclass(frozen=True)
class SetupVariable:
    """One environment variable a protocol reads."""

    name: str
    prompt: str
    required: bool = True
    secret: bool = False
    default: str = ""


@dataclass(frozen=True)
class ProtocolSetup:
    """How to configure one AI protocol."""

    name: str
    summary: str
    variables: tuple[SetupVariable, ...] = ()
    #: Optional extra this protocol needs, e.g. ``"gemini"``.
    extra: str | None = None
    #: Module the extra provides, used to check it is installed.
    extra_module: str | None = None


PROTOCOLS: tuple[ProtocolSetup, ...] = (
    ProtocolSetup(
        name="GEMINI",
        summary="Google Gemini API (cloud)",
        variables=(
            SetupVariable("ATLAS_GEMINI_API_KEY", "Gemini API key", secret=True),
            SetupVariable(
                "ATLAS_GEMINI_MODEL",
                "Gemini model name (see https://ai.google.dev/gemini-api/docs/models)",
            ),
        ),
        extra="gemini",
        extra_module="google.genai",
    ),
    ProtocolSetup(
        name="ANTHROPIC",
        summary="Anthropic Claude API (cloud)",
        variables=(
            SetupVariable("ATLAS_AI_API_KEY", "Anthropic API key", secret=True),
            SetupVariable("ATLAS_AI_MODEL", "Model", default="claude-opus-5-5"),
        ),
    ),
    ProtocolSetup(
        name="OPENAI_COMPATIBLE",
        summary="OpenAI, LM Studio, or any OpenAI-compatible server",
        variables=(
            SetupVariable(
                "ATLAS_AI_ENDPOINT",
                "Base URL, without /chat/completions",
                default="http://localhost:1234/v1",
            ),
            SetupVariable("ATLAS_AI_MODEL", "Model name"),
            SetupVariable(
                "ATLAS_AI_API_KEY",
                "API key (leave empty for local servers)",
                required=False,
                secret=True,
            ),
        ),
    ),
    ProtocolSetup(
        name="OLLAMA",
        summary="Local models through Ollama",
        variables=(
            SetupVariable(
                "ATLAS_AI_ENDPOINT",
                "Ollama URL",
                required=False,
                default="http://localhost:11434",
            ),
            SetupVariable("ATLAS_AI_MODEL", "Model name, e.g. qwen2.5-coder:7b"),
        ),
    ),
    ProtocolSetup(
        name="SCRIPTED",
        summary="Offline demo provider: canned output, no key, no network",
    ),
)


def protocol_setup(name: str) -> ProtocolSetup | None:
    """Return the setup entry for ``name`` (case-insensitive), if known."""
    wanted = name.upper()
    return next((p for p in PROTOCOLS if p.name == wanted), None)


def extra_installed(setup: ProtocolSetup) -> bool:
    """True when the protocol needs no extra, or its extra is installed."""
    if setup.extra_module is None:
        return True
    try:
        return importlib.util.find_spec(setup.extra_module) is not None
    except ModuleNotFoundError:
        return False


def render_env_file(protocol: ProtocolSetup, values: dict[str, str]) -> str:
    """Render a ``.env`` file selecting ``protocol`` with ``values``.

    Variables without a value are written commented out, so the file shows
    what can be set.
    """
    lines = [
        "# ATLAS configuration, written by `atlas init`.",
        "# Check it with `atlas doctor`. Keep this file out of version control.",
        "",
        f"ATLAS_AI_PROTOCOL={protocol.name}",
    ]
    for variable in protocol.variables:
        value = values.get(variable.name, "")
        if value:
            lines.append(f"{variable.name}={json.dumps(value)}")
        else:
            lines.append(f"# {variable.name}=")
    return "\n".join(lines) + "\n"


class CheckStatus(StrEnum):
    """Outcome of one configuration check."""

    OK = "ok"
    WARN = "warn"
    FAIL = "fail"


@dataclass(frozen=True)
class ConfigurationCheck:
    """One line of an ``atlas doctor`` report."""

    name: str
    status: CheckStatus
    detail: str
    fix: str = ""


@dataclass(frozen=True)
class ConfigurationReport:
    """All configuration checks, in the order they ran."""

    checks: tuple[ConfigurationCheck, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        """True when no check failed (warnings allowed)."""
        return all(check.status != CheckStatus.FAIL for check in self.checks)


def _check_env_file() -> tuple[ConfigurationCheck, str | None]:
    path = find_dotenv(usecwd=True)
    if path:
        return ConfigurationCheck("Config file", CheckStatus.OK, path), path
    return (
        ConfigurationCheck(
            "Config file",
            CheckStatus.WARN,
            "No .env found here or in any parent directory; using the "
            "environment only.",
            "Run 'atlas init' to create one.",
        ),
        None,
    )


def _check_protocol(settings: Settings) -> list[ConfigurationCheck]:
    setup = protocol_setup(settings.ai_protocol)
    if setup is None:
        known = ", ".join(p.name for p in PROTOCOLS)
        return [
            ConfigurationCheck(
                "AI protocol",
                CheckStatus.FAIL,
                f"Unknown protocol {settings.ai_protocol!r}.",
                f"Set ATLAS_AI_PROTOCOL to one of: {known}.",
            )
        ]
    checks = [
        ConfigurationCheck(
            "AI protocol",
            CheckStatus.WARN if setup.name == "SCRIPTED" else CheckStatus.OK,
            f"{setup.name} -- {setup.summary}",
            "Proposals will be canned demo text. Run 'atlas init' to use a real model."
            if setup.name == "SCRIPTED"
            else "",
        )
    ]
    missing = [
        variable.name
        for variable in setup.variables
        if variable.required and not _setting_value(settings, variable.name)
    ]
    if missing:
        checks.append(
            ConfigurationCheck(
                "Protocol settings",
                CheckStatus.FAIL,
                f"Missing: {', '.join(missing)}.",
                "Set them in .env (run 'atlas init') or the environment.",
            )
        )
    elif setup.variables:
        checks.append(
            ConfigurationCheck(
                "Protocol settings", CheckStatus.OK, "All required values are set."
            )
        )
    if not extra_installed(setup):
        checks.append(
            ConfigurationCheck(
                "Protocol package",
                CheckStatus.FAIL,
                f"{setup.name} needs the '{setup.extra}' extra, which is not "
                "installed.",
                f"pip install 'atlas-eng[{setup.extra}]'",
            )
        )
    return checks


def _setting_value(settings: Settings, variable: str) -> str:
    field_name = variable.removeprefix("ATLAS_").lower()
    value = getattr(settings, field_name, None)
    return str(value) if value else ""


def _check_workspace(settings: Settings) -> ConfigurationCheck:
    root = settings.workspace_root.resolve()
    probe_dir = (
        root
        if root.exists()
        else next((parent for parent in root.parents if parent.exists()), None)
    )
    if probe_dir is None or not os.access(probe_dir, os.W_OK):
        return ConfigurationCheck(
            "Workspace",
            CheckStatus.FAIL,
            f"{root} is not writable.",
            "Set ATLAS_WORKSPACE_ROOT to a directory you can write to.",
        )
    detail = str(root) if root.exists() else f"{root} (created on first use)"
    return ConfigurationCheck("Workspace", CheckStatus.OK, detail)


def _check_embeddings(settings: Settings) -> ConfigurationCheck | None:
    if not settings.embedding_enabled:
        return None
    config = ProviderConfig(
        protocol=settings.embedding_protocol or settings.ai_protocol,
        endpoint=settings.embedding_endpoint or settings.ai_endpoint,
        model=settings.embedding_model,
        api_key=settings.embedding_api_key or settings.ai_api_key,
    )
    try:
        EmbeddingFactory().resolve(config, settings)
    except AIException as error:
        return ConfigurationCheck(
            "Semantic retrieval",
            CheckStatus.WARN,
            f"Enabled but misconfigured; falling back to newest-first: {error}",
            "Fix the ATLAS_EMBEDDING_* settings or set ATLAS_EMBEDDING_ENABLED=false.",
        )
    return ConfigurationCheck("Semantic retrieval", CheckStatus.OK, config.protocol)


def _check_langfuse(env_path: str | None) -> ConfigurationCheck:
    file_values = dotenv_values(env_path) if env_path else {}
    keys = all(
        os.environ.get(name) or file_values.get(name)
        for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")
    )
    installed = importlib.util.find_spec("langfuse") is not None
    if keys and not installed:
        return ConfigurationCheck(
            "Langfuse tracing",
            CheckStatus.WARN,
            "Keys are set but the package is not installed.",
            "pip install 'atlas-eng[langfuse]'",
        )
    return ConfigurationCheck(
        "Langfuse tracing", CheckStatus.OK, "on" if keys else "off (optional)"
    )


def _check_live(settings: Settings) -> ConfigurationCheck:
    """Send one tiny real request through the configured provider."""
    config = ProviderConfig(
        protocol=settings.ai_protocol,
        endpoint=settings.ai_endpoint,
        model=settings.ai_model,
        api_key=settings.ai_api_key,
        timeout_seconds=settings.ai_timeout_seconds,
    )
    started = time.monotonic()
    try:
        provider = ProtocolFactory().resolve(config, settings)
        PromptExecutor(provider, IdentityContextStrategy()).execute(
            SummaryPromptTemplate(),
            ContextPayload(serialized_context="ATLAS configuration check."),
            SummaryDraft,
            user_instructions="Reply with a one-sentence summary.",
        )
    except AIException as error:
        return ConfigurationCheck(
            "Live request",
            CheckStatus.FAIL,
            str(error),
            "Fix the settings above, then run 'atlas doctor --live' again.",
        )
    elapsed = time.monotonic() - started
    return ConfigurationCheck(
        "Live request",
        CheckStatus.OK,
        f"The model returned a valid structured response in {elapsed:.1f}s.",
    )


def diagnose(*, live: bool = False) -> ConfigurationReport:
    """Check the current configuration without starting the platform.

    Offline unless ``live`` is set, in which case one small request is sent
    to the configured AI provider (this may cost a few tokens).
    """
    env_check, env_path = _check_env_file()
    settings = Settings(_env_file=env_path)  # type: ignore[call-arg]
    checks = [env_check, *_check_protocol(settings), _check_workspace(settings)]
    embeddings = _check_embeddings(settings)
    if embeddings is not None:
        checks.append(embeddings)
    checks.append(_check_langfuse(env_path))
    if live and all(check.status != CheckStatus.FAIL for check in checks):
        checks.append(_check_live(settings))
    return ConfigurationReport(tuple(checks))


def make_demo_workspace() -> Path:
    """A fresh directory for ``atlas demo`` to write its throwaway project to."""
    return Path(tempfile.mkdtemp(prefix="atlas-demo-"))
