"""Deterministic, offline protocol adapter (``ATLAS_AI_PROTOCOL=SCRIPTED``).

Returns a fixed, schema-valid draft for every prompt template without any
network access or credentials. It exists so the whole pipeline -- CLI, SDK,
evals, CI -- can be exercised end to end with no API key, and so a new user
can see what ATLAS does before configuring a real provider.

The content is canned demonstration text, not model output. Nothing here
should be mistaken for a real engineering proposal.

Failure modes for tests are selected with the model name
(``ATLAS_AI_MODEL``): ``malformed-json``, ``schema-violation``,
``truncated`` and ``provider-error``. Any other value behaves normally.
"""

import hashlib
import json
import math
import re
from collections.abc import Callable, Sequence
from typing import Any

from atlas_eng.engine.ai.config import ProviderConfig
from atlas_eng.engine.ai.embeddings import EmbeddingProvider
from atlas_eng.engine.ai.exceptions import AIProviderException
from atlas_eng.engine.ai.provider import AIProvider
from atlas_eng.engine.domain.ai import AIRequest, AIResponse, ProviderCapabilities

FAULT_MALFORMED_JSON = "malformed-json"
FAULT_SCHEMA_VIOLATION = "schema-violation"
FAULT_TRUNCATED = "truncated"
FAULT_PROVIDER_ERROR = "provider-error"

_GROUNDED_EVIDENCE_MARKER = "GROUNDED EVIDENCE"
_CANDIDATE_LINE = re.compile(r"^\[\d+\] ", re.MULTILINE)
_EMBEDDING_DIMENSIONS = 64
_CONTEXT_WINDOW = 32_000
_TRUNCATION_DIVISOR = 2


def _grounded_evidence(request: AIRequest) -> list[dict[str, Any]]:
    """Recover the retrieved evidence the research prompt asks to reproduce.

    The research stage rejects any draft whose evidence does not match what
    was retrieved, so the scripted draft must echo it back exactly as a real
    model is instructed to.
    """
    context = request.context.serialized_context
    marker_at = context.rfind(_GROUNDED_EVIDENCE_MARKER)
    if marker_at == -1:
        return []
    array_at = context.find("[", context.find(":\n", marker_at))
    if array_at == -1:
        return []
    try:
        parsed, _ = json.JSONDecoder().raw_decode(context[array_at:])
    except json.JSONDecodeError:
        return []
    return [item for item in parsed if isinstance(item, dict)]


def _research(request: AIRequest) -> dict[str, Any]:
    evidence = _grounded_evidence(request)
    # Findings must cite evidence and opportunities must cite findings, so
    # both are only emitted when there is evidence to point at.
    findings = [
        {
            "title": "Demo finding: human approval gates reduce rework",
            "summary": (
                "Scripted demonstration finding. Reviewing each proposal "
                "before it is committed catches scope errors early."
            ),
            "evidence_indices": [0],
        }
    ]
    return {
        "problem_statement": (
            "Scripted demo: the team needs a traceable path from an idea to "
            "an approved engineering plan."
        ),
        "objectives": [
            "Establish the problem and its constraints",
            "Identify the smallest deliverable that proves the approach",
        ],
        "evidence": evidence,
        "findings": findings if evidence else [],
        "constraints": [
            {
                "description": "Must run without external services in CI.",
                "impact": "Every stage needs a deterministic offline path.",
                "finding_indices": [0] if evidence else [],
            }
        ],
        "assumptions": [
            {
                "description": "A single maintainer reviews every proposal.",
                "risk": "Review becomes a bottleneck as the project grows.",
            }
        ],
        "opportunities": (
            [
                {
                    "title": "Reuse approved decisions across projects",
                    "description": "Publish reviewed knowledge for later stages.",
                    "finding_indices": [0],
                }
            ]
            if evidence
            else []
        ),
    }


def _planning(_request: AIRequest) -> dict[str, Any]:
    return {
        "scope_statement": (
            "Scripted demo: deliver a minimal, reviewable first release."
        ),
        "deliverables": [
            {
                "title": "Working command-line workflow",
                "description": "A user can take a project through every stage.",
            }
        ],
        "milestones": [
            {
                "title": "M1: Walking skeleton",
                "description": "One thin slice through every stage.",
                "epics": [
                    {
                        "title": "Core pipeline",
                        "description": "Stage execution and approval.",
                        "tasks": [
                            {
                                "title": "Implement stage execution",
                                "description": "Generate and store a draft.",
                                "subtasks": [{"title": "Persist the proposal"}],
                            }
                        ],
                    }
                ],
            }
        ],
    }


def _architecture(_request: AIRequest) -> dict[str, Any]:
    return {
        "design_summary": (
            "Scripted demo: a layered design with a stateless core and thin "
            "client adapters."
        ),
        "drivers": [
            {
                "driver_type": "QUALITY_ATTRIBUTE",
                "description": "Every decision must be auditable.",
            }
        ],
        "components": [
            {
                "name": "Core",
                "description": "Owns the domain model and workflow rules.",
                "responsibilities": ["Validate and commit proposals"],
                "public_interfaces": ["execute_stage"],
                "owned_data": ["project snapshots"],
                "internal_dependencies": [],
                "external_dependencies": [],
            },
            {
                "name": "CLI",
                "description": "Translates terminal commands into core calls.",
                "responsibilities": ["Parse arguments", "Render results"],
                "public_interfaces": [],
                "owned_data": [],
                "internal_dependencies": ["Core"],
                "external_dependencies": [],
            },
        ],
        "decisions": [
            {
                "title": "Store project state as files",
                "status": "ACCEPTED",
                "context": "Project history must be reviewable in git.",
                "decision": "Persist every snapshot as a file in the repo.",
                "consequences": "No database to operate; large projects scan files.",
            }
        ],
        "risks": [
            {
                "title": "Concurrent writers",
                "description": "Two processes may write the same project.",
                "severity": "medium",
            }
        ],
    }


def _evaluation(_request: AIRequest) -> dict[str, Any]:
    return {
        "synthesis": (
            "Scripted demo: the plan and architecture are consistent and "
            "ready to implement."
        ),
        "findings": [
            {
                "title": "Traceability is complete",
                "summary": "Each decision links back to an approved stage.",
                "severity": "info",
                "category": "traceability",
            }
        ],
    }


def _knowledge(_request: AIRequest) -> dict[str, Any]:
    return {
        "title": "Require human approval before commit",
        "content": "No generated proposal is written without explicit review.",
        "category": "principle",
        "tags": ["review", "demo"],
        "rationale": "Keeps the permanent record trustworthy.",
    }


def _evidence_summaries(request: AIRequest) -> dict[str, Any]:
    count = len(_CANDIDATE_LINE.findall(request.context.serialized_context))
    return {
        "summaries": [
            f"Scripted summary of retrieved paper {index + 1}."
            for index in range(count)
        ]
    }


def _summary(_request: AIRequest) -> dict[str, Any]:
    return {"summary": "Scripted demo summary of the supplied context."}


# Keyed by the JSON-schema ``title`` pydantic derives from each draft class,
# which is the only signal a provider receives about what is being asked for.
_SCRIPTS: dict[str, Callable[[AIRequest], dict[str, Any]]] = {
    "ResearchProposalDraft": _research,
    "PlanningProposalDraft": _planning,
    "ArchitectureProposalDraft": _architecture,
    "EvaluationProposalDraft": _evaluation,
    "KnowledgeCandidateDraft": _knowledge,
    "EvidenceSummaryBatchDraft": _evidence_summaries,
    "SummaryDraft": _summary,
}


def _count_tokens(text: str) -> int:
    return len(text.split())


class ScriptedAIProvider(AIProvider):
    """Offline provider returning a canned, schema-valid draft per template."""

    def __init__(
        self,
        config: ProviderConfig | None = None,
        *,
        stubbed_response: str | None = None,
    ) -> None:
        self._fault = (config.model or "").lower() if config else ""
        #: When set, returned verbatim instead of the scripted draft. Lets
        #: tests and eval tasks drive one specific response through the
        #: real pipeline.
        self.stubbed_response = stubbed_response

    def generate(self, request: AIRequest) -> AIResponse:
        """Return the scripted draft for the requested schema."""
        if self._fault == FAULT_PROVIDER_ERROR:
            raise AIProviderException(
                "Scripted provider failure (ATLAS_AI_MODEL=provider-error)."
            )
        content = self._content(request)
        finish_reason = "stop"
        if self._fault == FAULT_MALFORMED_JSON:
            content = "Sure! Here is the proposal you asked for: {not json"
        elif self._fault == FAULT_SCHEMA_VIOLATION:
            content = json.dumps({"unexpected_field": True})
        elif self._fault == FAULT_TRUNCATED:
            content = content[: len(content) // _TRUNCATION_DIVISOR]
            finish_reason = "length"
        prompt = request.prompt
        prompt_text = f"{prompt.system_prompt} {prompt.context} {prompt.task}"
        return AIResponse(
            content=content,
            usage_metrics={
                "prompt_tokens": _count_tokens(prompt_text),
                "completion_tokens": _count_tokens(content),
            },
            finish_reason=finish_reason,
        )

    def _content(self, request: AIRequest) -> str:
        if self.stubbed_response is not None:
            return self.stubbed_response
        title = (request.response_schema or {}).get("title")
        script = _SCRIPTS.get(title) if isinstance(title, str) else None
        if script is None:
            raise AIProviderException(
                f"The SCRIPTED protocol has no canned response for schema "
                f"{title!r}. Configure a real AI protocol for this request."
            )
        return json.dumps(script(request))

    def capabilities(self) -> ProviderCapabilities:
        """Describe the scripted provider's fixed feature set."""
        return ProviderCapabilities(
            structured_output=True,
            streaming_support=False,
            tool_calling=False,
            image_input=False,
            reasoning_support=False,
            context_window=_CONTEXT_WINDOW,
        )


class ScriptedEmbeddingProvider(EmbeddingProvider):
    """Offline embeddings: a hashed bag-of-words vector, unit-normalized.

    Texts sharing words get similar vectors, so ranking behaves sensibly in
    tests, but this is not a semantic model and must not be used to judge
    retrieval quality.
    """

    @property
    def model_id(self) -> str:
        """Identify the scripted vector space."""
        return f"SCRIPTED:hashed-bow-{_EMBEDDING_DIMENSIONS}"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one deterministic vector per input text."""
        return [self._embed_one(text) for text in texts]

    @staticmethod
    def _embed_one(text: str) -> list[float]:
        vector = [0.0] * _EMBEDDING_DIMENSIONS
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            digest = hashlib.sha256(word.encode()).digest()
            vector[digest[0] % _EMBEDDING_DIMENSIONS] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            # An all-zero vector has no direction; give empty text a fixed one.
            vector[0] = 1.0
            return vector
        return [value / norm for value in vector]
