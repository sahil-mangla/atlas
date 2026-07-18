# Phase 13: Engineering Knowledge Layer — Implementation Plan

**Status:** Revised draft for architectural review  
**Scope:** Planning only — no code changes  
**Baseline:** Phases 1–12 complete and locked  
**Target location:** `engine/knowledge/`

---

## 1. Executive Summary

### Overall Objective

Introduce the **Engineering Knowledge Layer** as an independent subsystem under `engine/knowledge/` that captures, reviews, publishes, retrieves, and lifecycle-manages **organizational engineering knowledge** derived from approved engineering artifacts.

This layer is distinct from:

| Concern | Owner | Phase 13 role |
|---|---|---|
| AI conversation history | `engine/memory/` | Unchanged |
| Prompt state / templates | `engine/prompt/` | Unchanged |
| Embeddings / vector search | Not in ATLAS v1 | Out of scope |
| Traceability validation | `engine/domain/traceability.py` + validators | Links only; no ownership |

Knowledge follows the locked lifecycle:

```
Approved Artifact → Knowledge Candidate → Human Review → Published Knowledge → Retrieved → Superseded / Deprecated
```

AI may propose candidates. AI may never publish. Published knowledge is immutable.

### Architectural Impact

Phase 13 adds a new engine subsystem and shifts **engineering context assembly orchestration** to Workflow:

```
WorkflowOrchestrationService
        │
        ├─► KnowledgeOrchestrationService.retrieve_for_stage()   [NEW]
        │
        ├─► ContextAssemblerService.assemble_context(knowledge=…)  [REFINED]
        │
        └─► StageExecutor → AIEngineeringService → PromptExecutor  [UNCHANGED internals]
```

**Refinements integrated in this revision:**

| Refinement | Design choice |
|---|---|
| Persistence root | `KnowledgePersistenceDocument` — serialization-only wrapper; no domain aggregate |
| Retrieval | Immutable stage profiles (`RESEARCH_PROFILE`, etc.); no strategy hierarchy |
| Extractors | Pluggable `KnowledgeExtractor` hierarchy retained (polymorphism justified) |
| Actor model | `KnowledgeActor` value object replaces stringly-typed owner fields |
| Deduplication | New `KnowledgeDeduplicationService` — deterministic, pre-persistence |
| Minimal SDK | One review command + extended workflow status |

**Locked decisions preserved (unchanged):**

- `engine/knowledge/` is an independent subsystem; not part of Workflow, Prompt Management, AI Runtime, Traceability, or Memory
- Workflow orchestrates knowledge; communicates only with `KnowledgeOrchestrationService`
- Workflow owns engineering knowledge retrieval; retrieval occurs before AI generation
- `ContextAssemblerService` never retrieves knowledge itself
- `PromptExecutor`, AI Runtime, and Multi-Protocol Runtime remain knowledge-agnostic
- Prompt Management unchanged except one new candidate template
- Knowledge is project-scoped in ATLAS v1
- Post-commit artifact extraction remains automatic
- Bootstrap remains the sole composition root
- Human approval mandatory before publication

### Scope

**In scope:**

- Domain entities (`KnowledgeCandidate`, `PublishedKnowledge`) and value objects
- Serialization root (`KnowledgePersistenceDocument`)
- Entity-centric repository over single-file persistence
- Internal services: Candidate, Approval, Retrieval, Lifecycle, Deduplication
- Pluggable extractors with explicit registry
- Immutable retrieval profiles per workflow stage
- Orchestration boundary, workflow integration, bootstrap wiring
- AI candidate drafts (propose-only)
- Deterministic deduplication before candidate persistence
- Filesystem persistence (`.atlas/knowledge.json`)
- Minimal public SDK surface
- Tests and documentation

**Out of scope:**

- Embeddings, vector search, semantic retrieval, AI-based deduplication
- LangFuse and external integrations (extension hooks only)
- Active workspace/org-scoped retrieval (query fields reserved)
- Public import/submit commands
- Traceability validation ownership

### User Review Items

1. Confirm `KnowledgeCategory` taxonomy (§2.1).
2. Confirm auto-extraction on post-commit for all four AI-assisted artifact types (§6.2).
3. Confirm deduplication rules: exact match blocks persistence; near-duplicate surfaces warning (§5.6).
4. Confirm minimal SDK: `ReviewKnowledgeCandidateCommand` + extended `WorkflowStatusResult` only (§6.7).
5. Confirm `KnowledgePersistenceDocument` is serialization-only with no business logic (§2.4).

### Open Questions

1. Near-duplicate threshold: normalized content equality only, or also title+category+tag overlap? (Recommended: exact content hash match = block; title+category match = warn.)
2. Org import JSON bundle schema — defer specific external formats to post-Phase 13?

---

## 2. Domain Design

### 2.1 Enumerations

Add to `engine/domain/enums.py`:

```python
class KnowledgeCategory(StrEnum):
    PRINCIPLE = "principle"
    PATTERN = "pattern"
    STANDARD = "standard"
    CONVENTION = "convention"
    DECISION_SUMMARY = "decision_summary"
    CONSTRAINT = "constraint"
    LESSON_LEARNED = "lesson_learned"

class KnowledgeSourceType(StrEnum):
    RESEARCH_SNAPSHOT = "research_snapshot"
    PLANNING_SNAPSHOT = "planning_snapshot"
    ARCHITECTURE_SNAPSHOT = "architecture_snapshot"
    EVALUATION_SNAPSHOT = "evaluation_snapshot"
    HUMAN_SUBMISSION = "human_submission"
    ORGANIZATIONAL_IMPORT = "organizational_import"
    AI_PROPOSAL = "ai_proposal"

class KnowledgeCandidateStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

class PublishedKnowledgeStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DEPRECATED = "deprecated"

class KnowledgeActorType(StrEnum):
    HUMAN = "human"
    AI = "ai"
    SYSTEM = "system"
    WORKFLOW = "workflow"
    PLUGIN = "plugin"
    IMPORT = "import"
    EXTERNAL = "external"       # reserved for future integrations

class KnowledgeScope(StrEnum):
    PROJECT = "project"
    WORKSPACE = "workspace"     # reserved; inactive in Phase 13
    ORGANIZATION = "organization"  # reserved; inactive in Phase 13
```

Add `ProposalType.KNOWLEDGE_CANDIDATE`. Retain `MEMORY_CANDIDATE` as deprecated alias for one release.

### 2.2 Value Objects

Create `engine/domain/knowledge.py`:

#### `KnowledgeActor`

Replaces all stringly-typed ownership fields (`proposed_by`, `published_by`, `submitted_by`). Represents any actor that creates, proposes, reviews, or publishes knowledge — not authorship alone.

```python
class KnowledgeActor(BaseModel):
    actor_type: KnowledgeActorType
    actor_id: str              # username, "ai", "workflow", import source id, etc.
    display_name: str = ""
```

Future actor types (`WORKFLOW`, `PLUGIN`, `EXTERNAL`) are defined now; Phase 13 uses `HUMAN`, `AI`, `SYSTEM`, and `IMPORT` only.

#### `KnowledgeProvenance`

```python
class KnowledgeProvenance(BaseModel):
    source_type: KnowledgeSourceType
    source_id: UUID
    source_description: str
    extracted_at: datetime
    actor: KnowledgeActor
```

#### `KnowledgeRetrievalQuery`

Future-proof without additional Phase 13 runtime complexity:

```python
class KnowledgeRetrievalQuery(BaseModel):
    scope: KnowledgeScope = KnowledgeScope.PROJECT
    project_id: UUID | None = None
    workspace_id: UUID | None = None     # reserved; ignored in Phase 13
    stage: WorkflowStage | None = None   # selects retrieval profile
    categories: list[KnowledgeCategory] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    max_entries: int = 20
```

Phase 13: only `KnowledgeScope.PROJECT` is valid; non-project scope rejected with explicit error.

#### `EngineeringKnowledgeContext`

```python
class EngineeringKnowledgeContext(BaseModel):
    entry_ids: list[UUID]
    serialized_section: str
    scope: KnowledgeScope = KnowledgeScope.PROJECT
```

#### `HumanKnowledgeSubmission`

```python
class HumanKnowledgeSubmission(BaseModel):
    title: str
    content: str
    category: KnowledgeCategory
    tags: list[str]
    actor: KnowledgeActor
```

#### `DeduplicationResult`

```python
class DeduplicationResult(BaseModel):
    is_exact_duplicate: bool
    is_near_duplicate: bool
    matching_published_id: UUID | None
    matching_candidate_id: UUID | None
    normalized_fingerprint: str
```

Reuse: `TraceabilityLink`, `EngineeringReview` (optional approval audit).

### 2.3 Primary Domain Entities

`KnowledgeCandidate` and `PublishedKnowledge` are the **primary domain entities**. Business invariants are enforced exclusively in services — not in a wrapping aggregate root.

#### `KnowledgeCandidate` (mutable, pre-publication)

```python
class KnowledgeCandidate(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    content: str
    category: KnowledgeCategory
    tags: list[str]
    rationale: str
    provenance: KnowledgeProvenance
    status: KnowledgeCandidateStatus
    author: KnowledgeActor
    review_comment: str | None
    reviewed_by: KnowledgeActor | None
    traceability_links: list[TraceabilityLink]
    deduplication_fingerprint: str       # set by DeduplicationService
    similar_to_published_id: UUID | None  # set when near-duplicate detected
    created_at: datetime
```

Optional lightweight helpers only: `is_pending()`, `is_terminal()` — no cross-entity mutation.

#### `PublishedKnowledge` (immutable content post-publish)

```python
class PublishedKnowledge(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    project_id: UUID
    title: str
    content: str
    category: KnowledgeCategory
    tags: list[str]
    version: int
    status: PublishedKnowledgeStatus
    provenance: KnowledgeProvenance
    traceability_links: list[TraceabilityLink]
    author: KnowledgeActor
    published_at: datetime
    supersedes_id: UUID | None
    superseded_by_id: UUID | None
    candidate_id: UUID
    deduplication_fingerprint: str
    scope: KnowledgeScope = KnowledgeScope.PROJECT
```

Status-only lifecycle transitions update status/link fields via service-controlled writes. Content is never mutated in place.

### 2.4 Persistence Root — Serialization Only

Introduce an explicit persistence wrapper so the repository does not hide an implicit aggregate:

```python
class KnowledgePersistenceDocument(BaseModel):
    """Serialization root for .atlas/knowledge.json.

    NOT a domain aggregate. Contains no business logic, invariant
    enforcement, or lifecycle methods. Exists solely to define the
    on-disk document shape.
    """
    project_id: UUID
    candidates: list[KnowledgeCandidate]
    published: list[PublishedKnowledge]
    schema_version: int = 1
```

**What it is:**

- The explicit JSON document shape written to `.atlas/knowledge.json`
- The serialization/deserialization target used directly by `FilesystemKnowledgeRepository`
- The unit the repository loads and saves atomically

**What it is NOT:**

- A domain aggregate root
- A container for business rules or lifecycle methods
- A substitute for service-layer ownership

**Why it exists:** Persisting all knowledge into a single `knowledge.json` file requires a document envelope. Without an explicit type, that envelope becomes a hidden aggregate inside the repository. `KnowledgePersistenceDocument` makes the serialization boundary explicit and keeps business logic in services.

Domain entities (`KnowledgeCandidate`, `PublishedKnowledge`) remain the primary conceptual units. Services operate on individual entities; the repository maps entities ↔ document.

### 2.5 AI Draft Model

Add to `engine/domain/ai_drafts.py`:

```python
class KnowledgeCandidateDraft(BaseModel):
    title: str
    content: str
    category: KnowledgeCategory
    tags: list[str]
    rationale: str
    source_snapshot_type: KnowledgeSourceType | None
    source_snapshot_id: UUID | None
```

Wrapped in `AIProposal[KnowledgeCandidateDraft]`. Does **not** register with `ProposalCommitService`.

### 2.6 Extend `ContextPayload`

In `engine/domain/ai.py`:

```python
knowledge_entry_ids: list[UUID] = Field(default_factory=list)
```

Replace hardcoded `"## Engineering Memory\nNone\n"` in `ContextAssemblerService` with the engineering knowledge section when provided.

### 2.7 Lifecycle and Versioning

Owned by `KnowledgeLifecycleService`:

| Transition | Behavior |
|---|---|
| Publish from approved candidate | Create `PublishedKnowledge` v1, `ACTIVE` |
| Supersede | New published entry v(n+1); old → `SUPERSEDED` |
| Deprecate | Status → `DEPRECATED`; content unchanged |

`KnowledgeApprovalService` delegates publish to `KnowledgeLifecycleService` atomically on human approve.

### 2.8 Traceability

Passive `TraceabilityLink` references to source snapshot UUIDs. No traceability subsystem ownership. Existence validation deferred.

### 2.9 Legacy Migration

- Deprecate `MemoryCandidate` in `engine/domain/conversation.py` with pointer to `KnowledgeCandidate`
- Retain `ProposalType.MEMORY_CANDIDATE` as alias for `KNOWLEDGE_CANDIDATE`

---

## 3. Package Structure

```
engine/knowledge/
├── __init__.py              # Export KnowledgeOrchestrationService only
├── exceptions.py
├── repository.py            # Entity-centric ops over KnowledgePersistenceDocument
├── fs_repository.py
├── serializers.py           # KnowledgePersistenceDocument ↔ JSON
├── profiles.py              # Immutable retrieval profiles (RESEARCH_PROFILE, etc.)
├── orchestration.py         # KnowledgeOrchestrationService (sole external boundary)
├── services.py
│   ├── KnowledgeCandidateService
│   ├── KnowledgeApprovalService
│   ├── KnowledgeRetrievalService
│   ├── KnowledgeLifecycleService
│   └── KnowledgeDeduplicationService
└── extractors/
    ├── base.py              # KnowledgeExtractor ABC + ExtractorRegistry
    ├── research.py          # ResearchKnowledgeExtractor
    ├── planning.py          # PlanningKnowledgeExtractor
    ├── architecture.py      # ArchitectureKnowledgeExtractor
    └── evaluation.py        # EvaluationKnowledgeExtractor
```

**Removed from prior revision:** `strategies/` package and `StrategyRegistry` — replaced by `profiles.py`.

### Module Responsibilities

| Module | Responsibility |
|---|---|
| `serializers.py` | Read/write `KnowledgePersistenceDocument`; corrupt file → `InvalidKnowledgeException` |
| `profiles.py` | Frozen retrieval configuration constants per workflow stage |
| `repository.py` | Load/save document; entity-level query/save helpers |
| `extractors/` | Artifact-specific extraction; read-only upstream repo access |
| `services.py` | All business rules and invariant enforcement |
| `orchestration.py` | Delegation only; sole external boundary |

### Dependency Rules

```
engine/workflow/     ──►  engine/knowledge/orchestration.py
engine/knowledge/    ──✗  engine/ai/
engine/ai/           ──✗  engine/knowledge/
engine/knowledge/extractors/  ──►  engine/research|planning|architecture|evaluation/ (read-only)
```

---

## 4. Repository Design

### 4.1 Interface

Entity-centric operations backed by explicit document persistence:

```python
class KnowledgeRepository(ABC):
    # Document (serialization root)
    def load_document(self, project_id: UUID) -> KnowledgePersistenceDocument | None: ...
    def save_document(self, document: KnowledgePersistenceDocument) -> None: ...

    # Candidates (operate on document.candidates)
    def save_candidate(self, candidate: KnowledgeCandidate) -> None: ...
    def get_candidate(self, project_id: UUID, candidate_id: UUID) -> KnowledgeCandidate | None: ...
    def list_candidates(
        self, project_id: UUID, status: KnowledgeCandidateStatus | None = None
    ) -> list[KnowledgeCandidate]: ...

    # Published (operate on document.published)
    def save_published(self, entry: PublishedKnowledge) -> None: ...
    def get_published(self, project_id: UUID, entry_id: UUID) -> PublishedKnowledge | None: ...
    def list_published(
        self, project_id: UUID, status: PublishedKnowledgeStatus | None = None
    ) -> list[PublishedKnowledge]: ...

    # Rollback
    def delete_all(self, project_id: UUID) -> None: ...
```

Entity methods internally: load document → mutate list → save document. This keeps single-file atomicity without embedding business logic in the repository.

### 4.2 Persistence Strategy

- **Technology:** JSON (consistent with `docs/architecture/persistence.md`)
- **File:** `<project_root>/.atlas/knowledge.json`
- **Document type:** `KnowledgePersistenceDocument`
- **Path resolution:** inject `ProjectRepository`; call `get_project_path(project_id)`
- **Missing file:** `load_document` returns `None`; services treat as empty document
- **Corrupt file:** raise `InvalidKnowledgeException`

### 4.3 Storage Layout

```
[Project Root]/
├── .atlas/
│   ├── project.json
│   ├── research.json
│   ├── planning.json
│   ├── architecture.json
│   ├── workflow.json
│   ├── memory.json
│   ├── evaluation.json
│   └── knowledge.json          # KnowledgePersistenceDocument
```

### 4.4 Version Storage

Published knowledge versions stored inline in `document.published[]` (append-only). Active retrieval filters `status == ACTIVE`.

### 4.5 Immutability Guarantees

| Layer | Guarantee |
|---|---|
| Domain | `PublishedKnowledge` frozen at creation |
| Service | `KnowledgeLifecycleService` creates new records for supersession; never edits content |
| Repository | `save_published` rejects content field changes on existing entries |
| Deduplication | Fingerprints computed once at candidate creation; stored on entity |
| AI layer | No repository access |

---

## 5. Service Design

### 5.1 KnowledgeOrchestrationService (External Boundary)

Sole entry point for Workflow and bootstrap. Delegates; no duplicated business logic.

| Method | Delegates to |
|---|---|
| `retrieve_for_stage(project_id, stage)` | `KnowledgeRetrievalService` |
| `extract_candidate_from_artifact(project_id, source_type, source_id)` | `ExtractorRegistry` → `KnowledgeCandidateService` |
| `submit_candidate(project_id, submission)` | `KnowledgeCandidateService` (internal) |
| `create_candidate_from_ai_proposal(project_id, draft)` | `KnowledgeCandidateService` |
| `import_candidates(project_id, bundle)` | `KnowledgeCandidateService` (internal; tests/bootstrap) |
| `list_pending_candidates(project_id)` | `KnowledgeCandidateService` |
| `process_candidate_review(project_id, candidate_id, decision, actor, feedback)` | `KnowledgeApprovalService` → `KnowledgeLifecycleService` on approve |
| `supersede_knowledge(...)` | `KnowledgeLifecycleService` |
| `deprecate_knowledge(...)` | `KnowledgeLifecycleService` |

### 5.2 KnowledgeCandidateService (Internal)

**Owner:** Candidate creation and pre-approval persistence.

| Method | Responsibility |
|---|---|
| `create_from_extractor_output(candidates)` | Run deduplication, persist non-blocked candidates |
| `create_from_submission(submission)` | Human-authored candidate |
| `create_from_ai_draft(draft, actor)` | AI-proposed candidate as `PENDING_REVIEW` |
| `create_from_import(entry, actor)` | Organizational import → candidate |
| `get_pending(project_id)` | Query `PENDING_REVIEW` candidates |
| `withdraw(project_id, candidate_id, actor)` | Human withdrawal |

**Pre-persistence flow (all creation paths):**

```
1. Build KnowledgeCandidate payload
2. KnowledgeDeduplicationService.check(candidate, existing published + pending)
3. If exact duplicate of ACTIVE published → skip persistence (return existing reference)
4. If exact duplicate of pending candidate → skip persistence
5. If near duplicate → set similar_to_published_id; persist with warning metadata
6. Set deduplication_fingerprint; repository.save_candidate()
```

Does **not:** approve, publish, retrieve, or embed extraction rules.

### 5.3 KnowledgeApprovalService (Internal)

**Owner:** Human review gate.

| Method | Responsibility |
|---|---|
| `approve_and_publish(project_id, candidate_id, actor, comment)` | Validates `actor.actor_type == HUMAN`; atomically approves + calls lifecycle publish |
| `reject(project_id, candidate_id, actor, comment)` | Terminal rejection |

**Invariants:**

- Rejects non-human actors (`AI`, `SYSTEM`, `WORKFLOW`, etc.)
- Publish and approve are one atomic operation
- Raises if candidate not `PENDING_REVIEW`
- Surfaces `similar_to_published_id` in review metadata when near-duplicate flagged

### 5.4 KnowledgeRetrievalService (Internal)

**Owner:** Read-only assembly of published knowledge for prompt injection.

**No polymorphic strategy hierarchy.** Selects an immutable retrieval profile based on workflow stage.

```python
# engine/knowledge/profiles.py
@dataclass(frozen=True)
class KnowledgeRetrievalProfile:
    stage: WorkflowStage
    default_categories: tuple[KnowledgeCategory, ...]
    default_tags: tuple[str, ...]
    max_entries: int

RESEARCH_PROFILE = KnowledgeRetrievalProfile(
    stage=WorkflowStage.RESEARCH,
    default_categories=(KnowledgeCategory.LESSON_LEARNED, KnowledgeCategory.CONSTRAINT),
    default_tags=(),
    max_entries=20,
)
PLANNING_PROFILE = KnowledgeRetrievalProfile(...)
ARCHITECTURE_PROFILE = KnowledgeRetrievalProfile(...)
EVALUATION_PROFILE = KnowledgeRetrievalProfile(...)

STAGE_PROFILES: dict[WorkflowStage, KnowledgeRetrievalProfile] = { ... }
```

**Retrieval algorithm (deterministic):**

1. Resolve profile from `STAGE_PROFILES[query.stage]`
2. Load `document.published` entries with `status == ACTIVE`
3. Apply category filter: `query.categories` if non-empty, else profile defaults
4. Apply tag intersection if `query.tags` non-empty, else profile defaults (if any)
5. Sort by `published_at` descending, then `id` ascending (stable tie-break)
6. Cap at `min(query.max_entries, profile.max_entries)`
7. Serialize to markdown via `build_context(entries) -> EngineeringKnowledgeContext`

**Does not:** call AI, mutate state, access upstream subsystem repos, or use polymorphic strategy classes.

### 5.5 KnowledgeLifecycleService (Internal)

**Owner:** Publication and post-publish lifecycle transitions.

| Method | Responsibility |
|---|---|
| `publish_from_candidate(candidate, publisher: KnowledgeActor)` | Create immutable `PublishedKnowledge` |
| `supersede(project_id, old_id, new_published)` | Link chain; old → `SUPERSEDED` |
| `deprecate(project_id, published_id, reason, actor: KnowledgeActor)` | Status → `DEPRECATED` |

No content mutation. Supersession requires a new approved candidate.

### 5.6 KnowledgeDeduplicationService (Internal)

**Owner:** Deterministic duplicate detection before candidate persistence.

| Method | Responsibility |
|---|---|
| `compute_fingerprint(title, content, category, tags)` | Normalized deterministic hash |
| `check(candidate, published, pending)` | Returns `DeduplicationResult` |

**Normalization rules (deterministic):**

```python
def normalize(text: str) -> str:
    return " ".join(text.lower().split())   # lowercase, collapse whitespace

fingerprint = sha256(f"{normalize(title)}|{normalize(content)}|{category}|{sorted(tags)}")
```

**Detection rules:**

| Condition | Action |
|---|---|
| Fingerprint matches ACTIVE `PublishedKnowledge` | Exact duplicate — block candidate persistence |
| Fingerprint matches `PENDING_REVIEW` candidate | Exact duplicate — block candidate persistence |
| Normalized title + category match existing ACTIVE entry (content differs) | Near duplicate — allow persistence; set `similar_to_published_id` |
| No match | Persist normally |

**Must NOT use:** AI, embeddings, vector search, semantic similarity, fuzzy matching.

**Interaction with repository:** Read-only — receives published/candidate lists from `KnowledgeCandidateService`; never writes.

**Interaction with approval:** Near-duplicate metadata surfaced to human reviewer via candidate fields; reviewer decides approve/reject.

### 5.7 Pluggable Extractors (Unchanged)

```python
class KnowledgeExtractor(ABC):
    @property
    @abstractmethod
    def source_type(self) -> KnowledgeSourceType: ...

    @abstractmethod
    def extract(self, project_id: UUID, source_id: UUID) -> list[KnowledgeCandidate]: ...
```

| Extractor | Reads | Extracts |
|---|---|---|
| `ResearchKnowledgeExtractor` | `ResearchRepository` | Takeaways, constraints, assumptions |
| `PlanningKnowledgeExtractor` | `PlanningRepository` | Scope statement, milestone summaries |
| `ArchitectureKnowledgeExtractor` | `ArchitectureRepository` | ADRs, design summary, component boundaries |
| `EvaluationKnowledgeExtractor` | `EvaluationRepository` | Synthesis, resolved blocking findings |

`ExtractorRegistry`: explicit `KnowledgeSourceType → KnowledgeExtractor` map. Resolved by orchestration. Registered in bootstrap only. No dynamic discovery.

Extractors emit candidate payloads — they do **not** persist or deduplicate. `KnowledgeCandidateService` handles both.

### 5.8 Ownership Matrix

| Concern | Owner |
|---|---|
| Extraction | `KnowledgeExtractor` + `ExtractorRegistry` |
| Deduplication | `KnowledgeDeduplicationService` |
| Candidate persistence | `KnowledgeCandidateService` |
| Human approval | `KnowledgeApprovalService` |
| Publication + lifecycle | `KnowledgeLifecycleService` |
| Retrieval configuration | `profiles.py` (immutable constants) |
| Retrieval execution | `KnowledgeRetrievalService` |
| Serialization shape | `KnowledgePersistenceDocument` + `serializers.py` |
| Document persistence | `KnowledgeRepository` |
| External API | `KnowledgeOrchestrationService` |
| Workflow sequencing | `WorkflowOrchestrationService` |
| Snapshot context (non-knowledge) | `ContextAssemblerService` |

No responsibility overlap.

---

## 6. Workflow Integration

### 6.1 Pre-Generation Retrieval

Update `WorkflowOrchestrationService.generate_proposal()`:

```python
def generate_proposal(self, project_id, user_instructions=""):
    workflow = self.workflow_repo.get_by_project_id(project_id)
    executor = self.registry.get_executor(workflow.current_stage)

    # 1. Workflow retrieves engineering knowledge
    knowledge_context = self.knowledge_orchestration.retrieve_for_stage(
        project_id, workflow.current_stage
    )

    # 2. ContextAssembler receives finished knowledge section (does not retrieve)
    context = self.context_assembler.assemble_context(
        project_id, engineering_knowledge=knowledge_context
    )

    # 3. Stage executor receives fully assembled context
    return executor.generate_proposal(
        project_id, user_instructions, context=context
    )
```

### 6.2 Post-Commit Candidate Extraction (Automatic)

In `process_review_decision()`, after successful `ProposalCommitService.commit_proposal()`:

```python
if commit_res.success and commit_res.committed_snapshot_id:
    self.knowledge_orchestration.extract_candidate_from_artifact(
        project_id=project_id,
        source_type=_source_type_for_stage(workflow.current_stage),
        source_id=commit_res.committed_snapshot_id,
    )
```

Extraction → deduplication → candidate persistence. Never auto-publishes.

### 6.3 Knowledge Candidate Review

New method on `WorkflowOrchestrationService`:

```python
def process_knowledge_review(
    self, project_id, candidate_id, decision,
    actor: KnowledgeActor, feedback=None,
):
    return self.knowledge_orchestration.process_candidate_review(
        project_id, candidate_id, decision, actor, feedback
    )
```

Separate from proposal commit path. Does not touch `ProposalCommitService`.

### 6.4 StageExecutor / AIEngineeringService Refinement

- `StageExecutor.generate_proposal()`: add optional `context: ContextPayload | None`
- `AIEngineeringService.generate()`: use injected context when provided; fall back to `assemble_context()` for test backward compatibility

`PromptExecutor` unchanged. AI Runtime unchanged.

### 6.5 Context Assembly

`ContextAssemblerService.assemble_context()`:

```python
def assemble_context(
    self,
    project_id: UUID,
    engineering_knowledge: EngineeringKnowledgeContext | None = None,
) -> ContextPayload:
```

- Injects `engineering_knowledge.serialized_section` into context
- Populates `knowledge_entry_ids` on `ContextPayload`
- Never calls `KnowledgeOrchestrationService` or `KnowledgeRepository`

### 6.6 Minimal Public SDK

**Phase 13 public surface — two extensions only:**

| Change | Purpose |
|---|---|
| `ReviewKnowledgeCandidateCommand` | Human approve/reject with `decision`, `candidate_id`, `actor` |
| Extend `WorkflowStatusResult` | Add `pending_knowledge_candidates: list[UUID]` |

**Not exposed in Phase 13 public API** (internal orchestration / tests only):

- List, submit, import, and separate approve/reject commands
- Published knowledge listing

CLI: one subcommand `atlas knowledge review`.

---

## 7. AI Integration

- **AI proposes:** optional `KnowledgeAIEngineeringService` + `KnowledgeCandidatePromptTemplate`; workflow passes draft to orchestration → deduplication → candidate service
- **AI never publishes:** enforced in `KnowledgeApprovalService` via `KnowledgeActorType` check
- **PromptExecutor:** unchanged; knowledge arrives via `ContextPayload.serialized_context`
- **Prompt Management:** one new template + registry entry only
- **Multi-Protocol Runtime:** unchanged

`KnowledgeAIEngineeringService` in `engine/ai/engineering_services.py` does **not** import `engine/knowledge/`.

---

## 8. Bootstrap Changes

Update `atlas/_bootstrap.py`:

```
1.  knowledge_repo = FilesystemKnowledgeRepository(project_repo)

2.  extractor_registry = ExtractorRegistry(
        ResearchKnowledgeExtractor(research_repo),
        PlanningKnowledgeExtractor(planning_repo),
        ArchitectureKnowledgeExtractor(architecture_repo),
        EvaluationKnowledgeExtractor(evaluation_repo),
    )

3.  deduplication_svc = KnowledgeDeduplicationService()
4.  candidate_svc = KnowledgeCandidateService(knowledge_repo, deduplication_svc)
5.  lifecycle_svc = KnowledgeLifecycleService(knowledge_repo)
6.  approval_svc = KnowledgeApprovalService(knowledge_repo, lifecycle_svc)
7.  retrieval_svc = KnowledgeRetrievalService(knowledge_repo)
8.  knowledge_orchestration = KnowledgeOrchestrationService(
        candidate_svc, approval_svc, retrieval_svc, lifecycle_svc, extractor_registry)

9.  orchestration_service = WorkflowOrchestrationService(
        ..., knowledge_orchestration=knowledge_orchestration)
```

**Rules preserved:**

- Bootstrap is sole composition root
- `KnowledgeOrchestrationService` is the only knowledge class referenced outside the package
- `ContextAssemblerService` does not receive `KnowledgeRepository`
- Retrieval profiles are module-level constants in `profiles.py` — no registry class needed
- Extractor registry: explicit registration, bootstrap-only, no dynamic discovery

Mirror wiring in `tests/support/test_bootstrap.py`.

---

## 9. Testing Strategy

### 9.1 Test Package Structure

```
tests/knowledge/
├── test_exceptions.py
├── test_serializers.py           # KnowledgePersistenceDocument round-trip
├── test_repository.py            # document load/save; entity ops
├── test_profiles.py              # profile constants; stage mapping completeness
├── test_deduplication.py         # fingerprint, exact/near duplicate rules
├── test_services.py              # candidate, approval, lifecycle, retrieval
├── test_extractors.py            # per-artifact extraction output
├── test_orchestration.py         # delegation, registry lookup
└── test_boundary.py              # import direction enforcement

tests/domain/test_knowledge.py    # KnowledgeActor, entities, query scope, DeduplicationResult
tests/workflow/test_orchestration.py  # retrieval-before-generate; post-commit extract
tests/ai/test_services.py         # assemble_context with knowledge section
tests/test_atlas/test_knowledge_commands.py  # ReviewKnowledgeCandidateCommand only
```

### 9.2 Unit Tests

| Target | Cases |
|---|---|
| `KnowledgePersistenceDocument` | Serialization round-trip; schema_version; empty document |
| `KnowledgeActor` | All actor types serialize; HUMAN-only approval gate |
| `KnowledgeDeduplicationService` | Exact match blocks; near match warns; normalization deterministic |
| `KnowledgeCandidateService` | Dedup invoked before every persist path; skip on exact duplicate |
| `KnowledgeApprovalService` | Approve+publish atomic; non-human actor rejected |
| `KnowledgeRetrievalService` | Profile selection per stage; deterministic sort; cap enforcement |
| `KnowledgeLifecycleService` | Publish, supersede, deprecate; no content mutation |
| `KnowledgeExtractor` (each) | Expected candidates from fixture snapshots |
| Serializers | Corrupt JSON → typed exception |

### 9.3 Integration Tests

- Full lifecycle: extract → dedup → pending → approve → published → retrieve in context
- Exact duplicate extraction skipped after prior publish
- Near duplicate flagged; human can still approve
- Supersede: v1 `SUPERSEDED`, v2 `ACTIVE`; retrieval returns v2 only
- Empty knowledge store: generation succeeds with empty knowledge section

### 9.4 Boundary Tests

- `engine/knowledge/` does not import `engine/ai/`
- `engine/ai/` does not import `engine/knowledge/`
- `KnowledgePersistenceDocument` has no methods beyond Pydantic model
- No `KnowledgeRetrievalStrategy` classes exist

### 9.5 Coverage Targets

| Area | Target |
|---|---|
| `engine/knowledge/` | ≥ 90% line coverage |
| `KnowledgeDeduplicationService` | 100% branch coverage |
| New workflow paths | 100% branch coverage |
| Overall engine | No regression |

---

## 10. Documentation Changes

### 10.1 New Documents

| Document | Content |
|---|---|
| `docs/architecture/engineering-knowledge-layer.md` | Subsystem purpose, lifecycle, boundaries, deduplication, persistence document |
| `docs/diagrams/knowledge-lifecycle.md` | Candidate → publish → retrieve → supersede |
| `docs/diagrams/knowledge-workflow-integration.md` | Retrieval before prompt; post-commit extraction |
| `docs/decisions/adr-003-engineering-knowledge-layer.md` | Lock Phase 13 decisions |

### 10.2 Updated Documents

| Document | Changes |
|---|---|
| `docs/architecture/system-overview.md` | Add Engineering Knowledge Layer; clarify Memory vs Knowledge |
| `docs/architecture/layered-architecture.md` | Knowledge retrieval step in execution flow |
| `docs/architecture/domain-model.md` | Entities + persistence document; no domain aggregate |
| `docs/architecture/persistence.md` | `knowledge.json` as `KnowledgePersistenceDocument` |
| `docs/architecture/engineering-workflow.md` | Knowledge review parallel to proposal review |
| `docs/architecture/intelligence-layer.md` | Workflow-owned context assembly includes knowledge |
| `docs/architecture/extension-guide.md` | Adding extractors and retrieval profiles |
| `docs/glossary.md` | Engineering Knowledge, Knowledge Candidate, Published Knowledge, Knowledge Actor |
| `docs/diagrams/proposal-lifecycle.md` | Post-commit extraction + deduplication step |
| `docs/diagrams/engineering-pipeline.md` | Knowledge retrieval gate |
| `docs/README.md` | Index new documents |
| `README.md` | Add `engine/knowledge/`; fix Memory subsystem description |
| `CHANGELOG.md` | Phase 13 entry |
| `PROGRESS.md` | Phase 13 tracking |

### 10.3 Blueprint Updates (informational)

| Document | Changes |
|---|---|
| `Blueprint/06-memory-architecture.md` | Cross-reference; clarify Memory scope |
| `Blueprint/09-service-contracts.md` | KnowledgeOrchestrationService + DeduplicationService contracts |
| `Blueprint/10-domain-models.md` | Knowledge entities, KnowledgeActor, persistence document |

---

## 11. Verification Plan

### 11.1 Automated Verification

```bash
uv run pytest
uv run mypy .
uv run ruff check .
uv run ruff format .
```

### 11.2 Architectural Verification

| Check | Expected |
|---|---|
| Persistence root explicit | `KnowledgePersistenceDocument` in serializers; no hidden aggregate in repository |
| No domain aggregate | No `Knowledge` class with business methods |
| No retrieval strategy hierarchy | Only `profiles.py` constants; no `KnowledgeRetrievalStrategy` |
| Extractors pluggable | Registry + four extractors; bootstrap-only registration |
| Actor typing | `KnowledgeActor` used; no raw owner strings |
| Deduplication deterministic | No AI/embeddings in dedup service |
| Dependency direction | `engine/workflow/` → orchestration only |
| AI isolation | No knowledge imports in `engine/ai/` |
| Human gate | Non-human `KnowledgeActorType` blocked from publish |
| Locked decisions | Workflow retrieves; ContextAssembler does not; PromptExecutor unchanged |

### 11.3 Manual Smoke Tests

1. **Extract + dedup:** Approve research proposal → candidates in `knowledge.json` with fingerprints; re-commit same artifact → no duplicate candidates
2. **Review:** `atlas knowledge review --approve` → published entry `ACTIVE` with `KnowledgeActor`
3. **Retrieve:** Planning `generate_proposal` → context contains `## Engineering Knowledge`
4. **Near duplicate:** Submit similar candidate → `similar_to_published_id` set; reviewer sees warning; can approve or reject
5. **Lifecycle:** Supersede → v1 `SUPERSEDED`, v2 `ACTIVE`
6. **Boundary:** Confirm `PromptExecutor` and adapter code paths unchanged

---

## Implementation Sequence

| Sprint | Deliverables |
|---|---|
| **S1** | Domain entities, `KnowledgeActor`, `KnowledgePersistenceDocument`, enums, serializers, entity-centric repository |
| **S2** | Extractors + registry, deduplication service, candidate/approval/lifecycle services, retrieval profiles |
| **S3** | Retrieval service, orchestration service, workflow integration, context assembler refinement |
| **S4** | AI candidate draft + template, minimal SDK, bootstrap wiring |
| **S5** | Tests (dedup, profiles, extractors, boundary), documentation, verification |

---

## Appendix A: Integration Points

| File | Change |
|---|---|
| `engine/domain/knowledge.py` | **New** — entities, value objects, persistence document, dedup result |
| `engine/domain/enums.py` | Knowledge enums, `KnowledgeActorType`, `KnowledgeScope` |
| `engine/domain/ai.py` | Extend `ContextPayload` |
| `engine/domain/ai_drafts.py` | `KnowledgeCandidateDraft` |
| `engine/domain/conversation.py` | Deprecation notice on `MemoryCandidate` |
| `engine/knowledge/` | **New package** |
| `engine/ai/services.py` | `assemble_context(engineering_knowledge=...)` |
| `engine/ai/engineering_services.py` | Optional pre-built context; `KnowledgeAIEngineeringService` |
| `engine/workflow/orchestration.py` | Knowledge orchestration injection |
| `engine/prompt/templates.py` | `KnowledgeCandidatePromptTemplate` |
| `atlas/_bootstrap.py` | Wire subsystem |
| `atlas/commands.py` | `ReviewKnowledgeCandidateCommand` only |
| `atlas/results.py` | Extend `WorkflowStatusResult` |
| `tests/support/test_bootstrap.py` | Mirror wiring |

## Appendix B: Explicit Non-Goals

- Embedding store, vector retrieval, semantic similarity
- AI-initiated publish path
- Retrieval strategy polymorphism (deferred until algorithms diverge)
- Domain aggregate root with business logic
- Knowledge logic in Prompt Management or Multi-Protocol Runtime
- Traceability validation ownership transfer
- Memory subsystem redesign

---

**End of Phase 13 Implementation Plan**
