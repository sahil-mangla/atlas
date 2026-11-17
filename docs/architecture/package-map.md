# Package Map

What each package under `atlas_eng/` is responsible for. For the rules on
which layer may import which, see [CONTRIBUTING](../../CONTRIBUTING.md#where-code-goes).

ATLAS is organized as a strict layered architecture: a stateless, protocol-
independent domain and engineering core (`atlas_eng/engine/`), a versioned public SDK
boundary (`atlas/`), a presentation layer that renders read models without
touching engine internals (`atlas_eng/presentation/`), and thin client adapters
(`atlas_eng/clients/`) that translate an external environment (CLI today; MCP, REST,
and IDE integrations are Version 2 scope) into calls against that SDK.

- **`atlas/`** -- Public Application Platform SDK exposing the `Atlas` facade,
  immutable command/result DTOs, and application exceptions.
  - **`atlas_eng/capabilities/`** -- Internal Capability Layer decomposing `Atlas`
    into five thin delegation classes -- Project, Workflow, WorkflowExecution,
    Knowledge, Presentation.
  - **`atlas_eng/contracts/`** -- Public Contract Layer -- versioned
    `RequestEnvelope`/`ResponseEnvelope`, the `PlatformErrorCode` error
    contract, and API versioning.
  - **`atlas_eng/adapters/`** -- Public Adapter Boundary -- the structural
    `PlatformAdapter` protocol and capability-negotiation manifest every
    client (CLI, IDE, MCP, AI, REST, Desktop) satisfies.
- **`atlas_eng/engine/domain/`** -- Strongly-typed, framework-independent Pydantic
  models representing the ubiquitous domain language of ATLAS, including the
  Engineering Design Language (EDL) components (`TraceabilityLink`,
  `ArtifactMetadata` composition, `EngineeringReview` contracts), AI proposal
  drafts (`ai_drafts.py`), and review feedback (`ai_feedback.py`).
- **`atlas_eng/engine/project/`** -- Project Subsystem: workspace initialization
  (`.atlas/`), loading, metadata discovery, and lifecycle states (initialized,
  active, paused, archived).
- **`atlas_eng/engine/memory/`** -- Memory Subsystem managing dialogue context and
  history.
- **`atlas_eng/engine/knowledge/`** -- Knowledge Subsystem: the Engineering Knowledge
  Layer collecting, deduplicating, retrieving (newest-first, or optionally
  semantic via sqlite-vec), and managing reviewed project-scoped engineering
  knowledge.
- **`atlas_eng/engine/workflow/`** -- Workflow Subsystem: execution readiness, phase
  transitions, and lifecycle orchestration.
- **`atlas_eng/engine/research/`** -- Research Subsystem: problem definition, evidence
  gathering, snapshotting, hypothesis validation.
- **`atlas_eng/engine/planning/`** -- Planning Subsystem: decomposing research into
  scopes, milestones, epics, tasks, subtasks, and dependencies.
- **`atlas_eng/engine/architecture/`** -- Architecture Subsystem: component modeling,
  architectural decisions, interface contracts, and risk analysis.
- **`atlas_eng/engine/evaluation/`** -- Evaluation Subsystem: readiness review and
  stage-completion evaluation.
- **`atlas_eng/engine/ai/`** -- AI Integration Subsystem: protocol adapters (Gemini,
  Anthropic, OpenAI-compatible, Ollama), context assembly, orchestration, and
  stateless engineering proposal services.
- **`atlas_eng/presentation/`** -- Presentation Layer: composes typed, immutable Views
  from the Atlas read-model API and renders them to JSON/Markdown/CLI,
  independent of any client adapter.
- **`atlas_eng/clients/`** -- Client adapters (CLI today; MCP/IDE/REST are Version 2)
  translating external execution environments to the public Atlas SDK.
- **`atlas_eng/shared/`** -- Common utilities and cross-cutting concerns.
  - **`atlas_eng/shared/observability/`** -- Request-scoped AI usage capture shared by
    the engine provider boundary and the Atlas request boundary.
- **`atlas_eng/observability/`** -- Trace schema, request instrumentation, and
  pluggable exporters for the platform boundary.
- **`evals/`** -- YAML task loader, benchmark runner, report generation, and
  baseline regression detection, plus the labelled knowledge-retrieval eval
  (`evals/retrieval/`).
