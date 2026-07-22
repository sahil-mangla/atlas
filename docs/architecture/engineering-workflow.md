# ATLAS Engineering Workflow

## Purpose
This document defines the structured workflow engine of the ATLAS platform. It outlines the engineering lifecycle stages, transition state machine rules, and the mechanisms used to evaluate stage readiness and human approval.

## Responsibilities
- Define the progression of a project through the nine sequential lifecycle stages.
- Document the valid forward and backward transition rules in the state machine.
- Detail the separation between stage objectives and readiness reviews.

## Non-Responsibilities
- Describing external continuous integration (CI) or deployment pipeline configurations.
- Prescribing specific programming language conventions or codebase coding styles.

---

## The Engineering Lifecycle Stages

ATLAS workflows guide the software development process through nine distinct stages, enforcing a logical sequence from concept to verification:

1. **Idea**: Captures initial high-level vision, product boundaries, and concept overview.
2. **Research**: Explores problem domain, gathers external evidence, and synthesizes findings.
3. **Problem Definition**: Refines concept and research into functional and non-functional requirements.
4. **Planning**: Decomposes requirements into milestones, epic groupings, and prioritized roadmaps.
5. **Architecture**: Establishes system component boundaries, interface contracts, and records ADRs.
6. **Implementation**: Generates implementation instructions and edits code files in the workspace.
7. **Review**: Validates code edits against architecture blueprints and target specifications.
8. **Iteration**: Addresses review feedback, refines code structure, and corrects defects.
9. **Completion**: Freezes final codebase state, updates documentation, and archives the milestone.

---

## Workflow State Machine & Transitions

The workflow engine enforces a deterministic transition map to prevent premature development steps while supporting iterative loop-backs:

```
                  ┌──────────────────────────────────────────────┐
                  │                                              ▼
Idea ──> Research ──> Problem Definition ──> Planning ──> Architecture ──> Implementation ──> Review ──> Iteration ──> Completion
                  ▲                      ▲            ▲                ▲                     │        │
                  └──────────────────────┴────────────┴────────────────┴─────────────────────┴────────┘
```

Research and Architecture also have direct shortcut edges to Planning and
Review respectively (not drawn above to keep the ASCII diagram readable) --
see the Valid Transitions Registry below and the rendered diagram in
[docs/diagrams/engineering-pipeline.md](../diagrams/engineering-pipeline.md).

### Valid Transitions Registry
Transitions are validated against the `WorkflowTransitionService.VALID_TRANSITIONS` registry:
- **Idea**: Can transition to **Research**.
- **Research**: Can transition to **Problem Definition**, directly to **Planning** (Problem Definition has no AI-generation support, so it is an optional manual detour, not a mandatory waypoint), or back to **Idea**.
- **Problem Definition**: Can transition to **Planning** or back to **Research**.
- **Planning**: Can transition to **Architecture** or back to **Problem Definition**.
- **Architecture**: Can transition to **Implementation**, directly to **Review** (Implementation has no AI-generation support, so it is likewise an optional manual detour), or back to **Planning**.
- **Implementation**: Can transition to **Review** or back to **Architecture** (e.g. if code implementation reveals design flaws).
- **Review**: Can transition to **Iteration**, **Completion**, or back to **Implementation**.
- **Iteration**: Can transition to **Completion**, **Review**, or back to **Implementation**.
- **Completion**: Can transition back to **Iteration** to address post-completion updates.

### Transition Guardrails
- **Human Approval Principle**: No transition is valid without `approval_status == ApprovalStatus.APPROVED` and a formal transition reason documented in `WorkflowHistoryEntry`.
- **Readiness Verification**: The orchestrator evaluates the current stage readiness before permitting transitions.

---

## Stage Objectives vs. Readiness Reviews

- **Active Objectives**: Defined in `DEFAULT_STAGE_OBJECTIVES` (e.g., "Record ADRs" for Architecture). These represent the target accomplishments for a stage.
- **Readiness Review** (`ReadinessReview`): Evaluated by the `WorkflowReadinessService`. It checks if any active objectives remain uncompleted. If objectives are outstanding, the readiness status is set to `EvaluationStatus.FAILED` with a list of `blocking_issues`.
- **Clearing objectives for human-driven stages**: Problem Definition, Implementation, Iteration, and Completion have no AI `StageExecutor`, so nothing commits a proposal to clear their objectives automatically. Use `atlas workflow complete-objective` to clear them one at a time -- see [Progressing through a human-driven stage](workflow-stages.md#progressing-through-a-human-driven-stage).

---

## Future Extensions
- Support for concurrent stage execution (e.g. parallel Research and Planning) with structured branch-merge resolutions.
- Project-specific workflow configurations defining custom stage maps and checklist requirements via `.atlas/workflow-config.json`.
