# ATLAS Persistence Architecture

## Purpose
This document defines the persistence architecture of the ATLAS platform. It outlines the repository abstraction pattern, details the concrete local filesystem storage layout, and explains the compensating rollback transactions used to ensure file system durability.

## Responsibilities
- Define the abstract repository boundaries separating business logic from storage technologies.
- Detail the physical file layout and naming conventions in the project workspace.
- Document the path resolution dependency inversion pattern.
- Explain the compensating transaction and rollback behaviors used during commits.

## Non-Responsibilities
- Describing relational SQL database constraints, indexing strategies, or query performance tuning.
- Outlining network file system synchronization protocols or remote storage APIs.

---

## Repository Abstraction & Dependency Inversion

ATLAS separates domain services from concrete storage technologies using the Repository Pattern. All service classes interact with abstract repository interfaces (e.g. `ArchitectureRepository`), keeping domain logic decoupled and easily testable.

### Path Resolution Dependency Inversion
Concrete repositories (such as `FilesystemArchitectureRepository`) must not hardcode directory locations. Instead:
1. They receive the abstract `ProjectRepository` through constructor injection.
2. They call `project_repo.get_project_path(project_id)` to resolve the canonical directory of the target project.
3. This ensures that even if projects are moved or located in custom paths, all child repositories resolve their file locations dynamically and consistently.

---

## Filesystem Storage Layout

Under the hybrid local model, all engine-owned engineering data is persisted
in a hidden `.atlas/` folder located in the project's root directory. A
second, repo-visible `atlas-proposals/` folder holds the human-readable
Markdown record of every proposal a human is meant to actually read and
review -- deliberately outside `.atlas/` so it shows up in the normal file
tree, `git status`, and PR diffs instead of being buried where only Atlas
looks (see ADR-005):

```
[Project Root Path]/
├── .atlas/
│   ├── project.json       # Project aggregate root metadata
│   ├── research.json      # Evidence, findings, and opportunities
│   ├── planning.json      # Roadmap task list and epics
│   ├── architecture.json  # Subsystem blueprints, constraints, and ADRs
│   ├── workflow.json      # Stage state, active checklists, and transition logs
│   ├── memory.json        # Dialogue histories and context logs
│   ├── evaluation.json    # Review reports and compliance results
│   ├── knowledge.json     # Reviewed candidates and active published knowledge
│   └── proposals/         # Pending proposal JSON (machine-readable source of truth)
├── atlas-proposals/
│   ├── pending/            # Proposal Markdown awaiting human review
│   └── approved/           # Proposal Markdown archived on approval
└── [Project Code Files]   # Application source code
```

Atlas never edits this project's `.gitignore` -- whether to commit or ignore
either `atlas-proposals/` subfolder is left entirely to the user.

---

## Serialization & Rollback Behavior

### 1. Serialization
ATLAS utilizes JSON for filesystem serialization. Pydantic models are serialized to JSON string structures (e.g. via `serialize_architecture` and `deserialize_architecture` helper modules) before writing to disk.

### 2. Compensating Filesystem Transactions
Since local filesystems do not support standard ACID database transactions, ATLAS implements a compensating unit-of-work pattern (`ProposalCommitUnitOfWork` in `engine/ai/unit_of_work.py`):

- **Backup Phase (`begin`)**: Before mutating files during a proposal commit, the unit of work queries the current state of all relevant aggregates (Research, Planning, Architecture, Evaluation) and creates isolated backup copies using Pydantic's `model_copy(deep=True)`.
- **Compensating Rollback (`rollback`)**: If any step of the proposal validation, transformation, or commit fails:
  1. The unit of work iterates through the backup copies.
  2. For aggregates that existed prior to the change, it invokes `repository.save(backup)` to overwrite mutations and restore the original files.
  3. For aggregates that did not exist (newly created during the flow), it calls `repository.delete(project_id)` to remove the newly created JSON files, returning the directory to its exact pre-mutation state.

### 3. Published Knowledge Immutability Invariant
To preserve absolute traceability and engineering integrity, published knowledge content (title, content, category, tags) is strictly immutable once written. The `KnowledgeRepository` enforces this persistence invariant at the serialization boundary. Any attempt to modify the contents of an existing published entry raises a `ValueError`. Changes must be made by publishing a new version that formally supersedes the previous entry via version and backlink pointers.

---

## Future Extensions
- Git-backed persistence repository that automatically commits JSON updates to local Git branches, establishing absolute revision histories.
- Delta-based file serialization to optimize write performance on large memory databases.
