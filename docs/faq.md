# ATLAS FAQ

A working-notes FAQ for orienting (or re-orienting) yourself in the ATLAS codebase.
Every answer is grounded in the current code and the documents in `docs/`; where an
answer paraphrases a doc, that doc is linked so you can go deeper.

---

## 1. What is ATLAS, in one paragraph?

ATLAS is a local-first **engineering operating system**, not a chat agent. It models a
software project as a persistent, structured domain (Project → Workflow → Research →
Planning → Architecture → Evaluation → Knowledge → Memory), lets AI providers propose
changes to that domain under strict constitutional rules, and requires a human to
approve anything before it becomes canonical. See
[`docs/architecture/system-overview.md`](architecture/system-overview.md) for the full
17-subsystem breakdown and [`docs/glossary.md`](glossary.md) for exact terminology.

---

## 2. Architecture & Layering

### 2.1 What are the major layers, top to bottom?

```
clients/        CLI, MCP, REST, IDE adapters — translate raw I/O into Atlas calls
atlas/          The public facade + platform layer (Commands, Results, Capabilities, Contracts)
presentation/   Read models → Views → Renderers (JSON / Markdown / CLI text)
engine/         Domain services: ai, architecture, domain, evaluation, knowledge,
                memory, planning, project, prompt, research, workflow
shared/         Cross-cutting utilities (e.g. atomic_write)
```

Dependency direction is one-way: `clients` → `atlas` → `presentation`/`engine` →
`engine/domain`. `engine/domain` and `atlas/exceptions` are the two "core" packages —
highest fan-in, zero outbound calls — everything depends on them, they depend on
nothing internal.

### 2.2 What's the one file to read first?

[`atlas/_service.py`](../atlas/_service.py) — the `Atlas` class. It's the single public
interface: every client (CLI, MCP, REST, IDE) ultimately calls through it. See
[`docs/architecture/application-platform.md`](architecture/application-platform.md).

### 2.3 Why does every `engine/<domain>/` package look identical?

Each domain (`ai`, `architecture`, `evaluation`, `knowledge`, `memory`, `planning`,
`project`, `research`, `workflow`) follows the same five-file template:

- `exceptions.py` — domain-specific error types
- `repository.py` — abstract persistence interface
- `fs_repository.py` — filesystem implementation of that interface
- `serializers.py` — domain object ⇄ JSON
- `services.py` (or `orchestration.py`) — the actual business logic

This is a deliberate convention, not an accident — see
[`docs/architecture/architecture-principles.md`](architecture/architecture-principles.md)
and [`docs/architecture/extension-guide.md`](architecture/extension-guide.md) for how to
add a new one.

### 2.4 What are the current architecture hotspots (highest fan-in)?

| Symbol | Fan-in | File |
|---|---|---|
| `parse_argv` | 49 | `clients/cli/parser.py` |
| `Atlas.create_project` | 25 | `atlas/_service.py` |
| `Renderer.render` | 24 | `presentation/renderers/registry.py` |
| `ProjectRepository.get_project_path` | 20 | `engine/project/repository.py` |
| `PromptLoader.load_registry` | 16 | `engine/prompt/loader.py` |
| `ArchitectureRepository.get_by_project_id` | 16 | `engine/architecture/repository.py` |

These are the functions most things route through — good places to look when tracing
"what breaks if I change X."

---

## 3. The Atlas Facade & Platform Layer

### 3.1 What's the difference between the named methods and `Atlas.handle()`?

`Atlas` exposes two calling conventions over the exact same underlying capabilities:

- **Named methods** (`create_project`, `transition_stage`, `execute_stage`, …) — stable,
  used by the CLI, tests, and direct SDK consumers.
- **`handle(RequestEnvelope) -> ResponseEnvelope`** — a single versioned doorway for
  out-of-process/protocol-driven clients (MCP, REST, IDE, AI agents), added in Phase 15.
  It dispatches on `type(envelope.command)` via a literal dict (no reflection), and maps
  `ApplicationError` subclasses to a stable `ErrorEnvelope`.

See [`docs/architecture/platform-layer.md`](architecture/platform-layer.md) and
[`docs/decisions/adr-004-platform-capability-contract-layer.md`](decisions/adr-004-platform-capability-contract-layer.md).

### 3.2 What are the five "Capabilities"?

`atlas/capabilities/`: `Project`, `Workflow`, `WorkflowExecution`, `Knowledge`,
`Presentation`. Each is a thin, independently-testable delegation layer that `Atlas`
composes in `__init__` — they hold no logic of their own beyond mapping engine
exceptions to platform errors and forwarding to `engine/` services.

### 3.3 What is a "Command" and a "Result"?

Every mutation into Atlas is an immutable Command DTO (`CreateProjectCommand`,
`TransitionStageCommand`, `ExecuteStageCommand`, …) and every response is an immutable
Result DTO (`ProjectResult`, `WorkflowStatusResult`, `ProposalResult`, …). This is the
Command-Result pattern referenced throughout `docs/architecture/application-platform.md`
— it's why the facade never leaks a raw engine entity or repository to callers.

---

## 4. Workflow & Lifecycle Stages

### 4.1 What are the actual workflow stages?

`engine/domain/enums.py::WorkflowStage` (9 stages, sequential):

```
IDEA → RESEARCH → PROBLEM_DEFINITION → PLANNING → ARCHITECTURE →
IMPLEMENTATION → REVIEW → ITERATION → COMPLETION
```

Of these, four have dedicated AI **stage executors** in
`engine/workflow/orchestration.py` — `ResearchStageExecutor`,
`PlanningStageExecutor`, `ArchitectureStageExecutor`, `EvaluationStageExecutor` — which
is what `execute_stage` invokes. Stages with no executor are skippable/human-only; see
`test_workflow_transition_service_allows_skipping_stages_with_no_executor`.

### 4.2 How does `transition_stage` decide what's legal?

`WorkflowTransitionService.transition_stage` (`engine/workflow/services.py:247-306`)
enforces: (a) the target is a legal next stage, (b) readiness — e.g. required
objectives are completed — before it will move forward, and (c) it records every
transition to `Workflow.record_transition` history so the sequence is auditable, not
just enforced. Backward transitions preserve already-completed stage state (see
`test_workflow_backward_transition_preserves_completed_stages`).

### 4.3 What's the difference between "transition_stage" and "execute_stage"?

- `transition_stage` moves the workflow's *current stage pointer* forward/backward — a
  pure state-machine operation, no AI involved.
- `execute_stage` runs that stage's AI **proposal generation** (research findings, a
  plan, an architecture doc, an evaluation) — see §5.

### 4.4 What is `complete_objective`?

Each active stage has a checklist of objectives. `complete_objective` marks one as
satisfied by explicit human action — decoupled from AI proposal approval, so a human
can unblock readiness manually even without running an AI stage. See
[`docs/architecture/engineering-workflow.md`](architecture/engineering-workflow.md).

---

## 5. AI Integration & the AI Constitution

### 5.1 What AI providers does ATLAS support, and how is a provider chosen?

`engine/ai/adapters/`: `anthropic.py`, `gemini.py`, `ollama.py`,
`openai_compatible.py` — each implements the `AIProvider` protocol
(`engine/ai/provider.py`: `generate()`, `capabilities()`). `ProtocolFactory`
(`engine/ai/factory.py`) resolves a provider name string to the matching adapter at
bootstrap time; nothing in `engine/` above the factory is provider-specific. See
[`docs/architecture/multi-protocol-ai-runtime.md`](architecture/multi-protocol-ai-runtime.md).

### 5.2 What is the "AI Constitution" and why does it matter?

A six-rule contract in
[`docs/architecture/ai-constitution.md`](architecture/ai-constitution.md) that every AI
code path must satisfy, each with a concrete code enforcement:

| Rule | Requirement | Enforced by |
|---|---|---|
| 1. Stateless generation | No session/history state in the generation engine | `AIOrchestrationService`/`AIProvider` treat every call as a self-contained request/response |
| 2. No direct mutation | AI can never write/delete repository files | `AIOrchestrationService` has no `.save()`/`.delete()` access — only emits a draft `AIProposal` |
| 3. Deterministic context boundary | Only approved snapshots reach the model | `ContextAssemblerService` freezes only `ArtifactStatus.APPROVED` state |
| 4. Human-in-the-loop gate | Every proposal needs explicit human approval | `process_review_decision` requires `ProposalDecision.APPROVE` from `KnowledgeActorType.HUMAN` — AI/SYSTEM approvals are rejected |
| 5. Atomic commit & rollback | Commit failures must not leave partial state | `ProposalCommitService` + `ProposalCommitUnitOfWork` deep-copy aggregates first, roll back on exception |
| 6. Strong schema enforcement | Malformed AI output must be rejected at the boundary | Pydantic `model_json_schema()` in prompts, `model_validate()` on response, raises `InvalidProposalException` on mismatch |

This is the single most important document for understanding *why* ATLAS is structured
the way it is — read it before changing anything AI-adjacent.

### 5.3 How does ATLAS stop the AI from hallucinating citations?

Each stage has a `ProposalValidator` in `engine/ai/engineering_services.py`. For
research, `ResearchProposalValidator.validate` checks that every `Finding` references
`evidence_indices` that actually exist in the `evidence` list *retrieved before
generation* (`engine/research/retrieval.py` + `engine/research/sources/`) — an
out-of-range or missing index raises `InvalidProposalException` before the proposal can
even reach human review. The model cannot cite something it wasn't given.

### 5.4 What happens when a proposal is generated?

`execute_stage` → `AIEngineeringService.generate` → provider call → per-stage
`ProposalValidator` → per-stage `ProposalTransformer` → a `ProposalStatus.DRAFT`
proposal is persisted (never auto-committed). A human then calls `approve_proposal` or
`reject_proposal` (with feedback, which is itself persisted).

---

## 6. Knowledge Subsystem

### 6.1 What is a "knowledge candidate," and how is it different from a proposal?

A proposal (§5) is stage-specific AI output (a research draft, a plan, …). A
**knowledge candidate** is a smaller, durable claim — a principle, pattern, standard,
convention, decision summary, constraint, or lesson learned
(`KnowledgeCategory` in `engine/domain/enums.py`) — extracted *from* an approved
artifact or submitted directly by a human, destined for the project's long-lived
knowledge base. See
[`docs/architecture/engineering-knowledge-layer.md`](architecture/engineering-knowledge-layer.md).

### 6.2 What's the candidate lifecycle?

```
KnowledgeCandidateStatus: PENDING_REVIEW → APPROVED | REJECTED | WITHDRAWN
PublishedKnowledgeStatus (post-approval): ACTIVE → SUPERSEDED | DEPRECATED
```

Services: `KnowledgeCandidateService.create` → `KnowledgeDeduplicationService.check`
(runs before creation, to avoid piling up near-duplicate knowledge) →
`KnowledgeApprovalService.reject` or `KnowledgeLifecycleService.publish_from_candidate`
→ later, `supersede`/`deprecate` for revision without deleting history.

### 6.3 What is `KnowledgeProvenance` / `KnowledgeActor`?

Every candidate records **who** proposed it — `KnowledgeActorType`: `HUMAN`, `AI`,
`SYSTEM`, `WORKFLOW`, `PLUGIN`, `IMPORT`, `EXTERNAL` — and its `KnowledgeProvenance`
(`engine/domain/knowledge.py`). Combined with `TraceabilityLink`
(`engine/domain/traceability.py`), you can always answer "where did this claim come
from" without re-reading chat history, because the answer is stored data, not
conversational context. See
[`docs/architecture/traceability.md`](architecture/traceability.md) and
[`docs/diagrams/knowledge-lifecycle.md`](diagrams/knowledge-lifecycle.md).

### 6.4 How are extractors used?

`engine/knowledge/extractors/` (`architecture.py`, `evaluation.py`, `planning.py`,
`research.py`) pull candidate knowledge out of an *approved* artifact automatically
after a stage commits, via `ExtractorRegistry.extract`. This is separate from AI
proposing knowledge directly — it's ATLAS mining its own already-approved history.

---

## 7. Persistence & Memory

### 7.1 Where does everything live on disk?

Each `engine/<domain>/fs_repository.py` is a filesystem-backed repository keyed by
project ID, using `shared/atomic_write.py::atomic_write_text` (fan-in 15 — used
everywhere state is persisted) to avoid partial writes. See
[`docs/architecture/persistence.md`](architecture/persistence.md) for path resolution
and compensating-rollback details.

### 7.2 What is `engine/memory/`, and how is it different from an AI chat's context?

`engine/memory/` is a project-scoped, persistent store for conversation history, design
outcomes, and context (`MemoryCategory`: `KNOWLEDGE`, `DECISION`, `CONTEXT`,
`ARTIFACT`) — it survives across sessions and CLI invocations by design (Rule 1 of the
AI Constitution requires the *generation engine* to be stateless; `engine/memory/` is
the explicit, inspectable mechanism by which prior context re-enters a new request,
rather than an opaque chat history).

---

## 7.3 Observability & Evaluation

### 7.3.1 Where are request traces captured?

At `Atlas.handle()`, the versioned envelope boundary. A trace records the
request ID, adapter, selected capability, latency, outcome, platform error code,
and aggregate AI token usage. Named methods remain supported and are not
automatically traced; the CLI currently uses those methods, while envelope
clients and the eval runner use `handle()`.

See [`docs/observability.md`](observability.md) and
[`docs/diagrams/observed-platform-request.md`](diagrams/observed-platform-request.md).

### 7.3.2 What happens when dispatch raises an unexpected exception?

The request receives an `error` trace with no platform error code, because no
`ResponseEnvelope` exists. The original exception is then re-raised unchanged.
If the exporter itself fails, the failure is logged and the request continues
normally.

### 7.3.3 How do I run the platform evaluations?

Run `uv run python -m evals`. The default suite uses a local Ollama model,
writes reports to the ignored `evals/runs/` directory, and compares results
against the tracked `evals/baselines/latest.json`. See
[`docs/evaluations.md`](evaluations.md) for provider overrides, task authoring,
and baseline updates.

---

## 8. Clients (CLI / MCP / REST / IDE)

### 8.1 What clients exist today?

`clients/cli/` is fully implemented (entry point: `clients/cli/application.py:main`).
`clients/mcp/`, `clients/rest/`, `clients/desktop/`, `clients/ide/` exist as stubs/dirs
for future adapters — all are meant to call through `Atlas.handle()` (§3.1) rather than
reimplementing logic.

### 8.2 How does the CLI turn `sys.argv` into a Command?

`clients/cli/parser.py::parse_argv` (fan-in 49, the single highest-fan-in symbol in the
repo) → `CommandParser` builds the typed Command → `Atlas` method → `CLIRenderer`
formats the Result. See [`docs/architecture/client-adapters.md`](architecture/client-adapters.md)
and [`docs/usage/cli.md`](usage/cli.md).

---

## 9. Presentation Layer

### 9.1 Why is there a separate `presentation/` layer instead of clients formatting
Results directly?

So that JSON/Markdown/CLI-text output is derived from one typed, immutable pipeline
instead of three ad hoc formatters: `Atlas.get_*_read_model()` →
`presentation/collectors/` compose a `View` → `presentation/renderers/registry.py`
picks a `Renderer` (`Renderer.render`, fan-in 24) → `RenderResult`. Presentation code
never touches repositories or engine services directly — only the read-model API. See
[`docs/architecture/presentation-layer.md`](architecture/presentation-layer.md) and
[`docs/diagrams/presentation-flow.md`](diagrams/presentation-flow.md).

---

## 10. Testing & Architecture Enforcement

### 10.1 Is the layering just convention, or is it actually enforced?

It's enforced by tests, not just docs. Examples:

- `tests/knowledge/test_boundary.py::test_no_ai_imports_in_knowledge` and
  `test_no_knowledge_imports_in_ai` — asserts the `knowledge` and `ai` domains cannot
  import each other.
- `tests/architecture/test_platform_boundaries.py` and
  `test_presentation_boundaries.py` — assert presentation/platform layers don't reach
  past their declared dependencies.
- `tests/architecture/test_workflow_docs_sync.py` — asserts the workflow *docs*
  actually list every stage and transition the *code* defines, so documentation can't
  silently drift from implementation.

### 10.2 What test suites exist, roughly?

`tests/domain/` (pure domain model), `tests/<engine-domain>/` (repository/service/
serializer per domain), `tests/architecture/` (boundary + doc-sync enforcement),
`tests/presentation/`, `tests/test_clients/`, `tests/test_atlas/`,
`tests/observability/`, and `tests/evals/` (end-to-end, command-level,
instrumentation, runner, and RC-numbered regression suites). 1,236 `TESTS` edges
in the knowledge graph link test functions to the code they exercise.

---

## 11. How ATLAS Compares to a Deep-Research Agent or a Simple LLM Agent

### 11.1 What's fundamentally different?

A deep-research mode or a bare agent produces an **artifact** (a report, an answer) in
one shot, in one chat, with no persisted structure. ATLAS produces a **governed,
queryable, evolving knowledge base**, where AI is one of several actors
(`KnowledgeActorType`) permitted to *propose* changes, always subject to the AI
Constitution (§5.2).

| Concern | Simple LLM agent / deep research | ATLAS |
|---|---|---|
| Output shape | Freeform prose/markdown | Typed, Pydantic-validated domain objects |
| Evidence citation | Trusted, unverified | Index-checked against the actual retrieved evidence set at generation time |
| Truth model | Model's answer is final | AI output is a `DRAFT` proposal; requires human `APPROVE` |
| State across sessions | Lives in one chat transcript | Persisted domain state + dedicated `engine/memory/` |
| Duplicate/contradictory output | Not prevented | `KnowledgeDeduplicationService.check` before candidate creation |
| Provenance | None, or "the AI said so" | `KnowledgeProvenance` + `TraceabilityLink` per candidate |
| Model vendor | Usually fixed to one provider | `ProtocolFactory` swaps Anthropic/Gemini/Ollama/OpenAI-compatible behind one interface |
| Process rigor | Single-shot, whatever the prompt asks | Enforced stage sequence + readiness gates (§4) |
| Failure handling | Silent bad output | Atomic commit + compensating rollback (Constitution Rule 5) |

### 11.2 When is ATLAS the wrong tool?

For a genuine one-off question ("what does this error mean," "summarize this paper"),
the validation/dedup/gate machinery is pure overhead with no payoff — a plain agent or
a deep-research mode answers faster. ATLAS earns its complexity when the goal is a
**long-lived, multi-session, multi-contributor, auditable body of engineering
knowledge** that must not silently drift or self-contradict over time.

---

## 12. Extending ATLAS

### 12.1 How do I add a new engineering lifecycle stage?

Follow [`docs/architecture/extension-guide.md`](architecture/extension-guide.md) —
covers adding the `WorkflowStage` enum value, a new `engine/<domain>/` package
following the five-file template (§2.3), a `StageExecutor`, and wiring it into
`WorkflowOrchestrationService`.

### 12.2 How do I add a new AI provider?

Implement `AIProvider` (`generate`, `capabilities`) in `engine/ai/adapters/`, register a
`_create_<provider>` factory function, and add it to `ProtocolFactory`'s registry in
`engine/ai/factory.py`. See
[`docs/architecture/multi-protocol-ai-runtime.md`](architecture/multi-protocol-ai-runtime.md).

### 12.3 How do I add a new View/renderer?

[`docs/guides/presentation-extension-guide.md`](guides/presentation-extension-guide.md)
walks through adding a new View kind end-to-end: read model → collector → View →
renderer registration.

---

## 13. Quick Reference

- **Entry point**: `clients/cli/application.py::main`
- **Facade**: `atlas/_service.py::Atlas`
- **AI Constitution**: [`docs/architecture/ai-constitution.md`](architecture/ai-constitution.md)
- **Glossary**: [`docs/glossary.md`](glossary.md)
- **ADR index**: [`docs/README.md`](README.md) §3
- **All architecture docs**: [`docs/README.md`](README.md)
- **Domain enums (single source of truth for state values)**: `engine/domain/enums.py`
