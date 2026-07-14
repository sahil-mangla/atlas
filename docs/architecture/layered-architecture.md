# ATLAS Layered Architecture

## Purpose
This document details the layered architecture of the ATLAS platform. It defines the structural boundaries, dependency rules, and separation of concerns that govern data flow and execution pathways across the system.

## Responsibilities
- Define the layered execution flow from user interface triggers down to LLM provider calls.
- Detail the validation, transformation, and commit flows that translate generated drafts into persisted domain state.
- Document decoupling strategies, dependency directions, and interface boundaries.

## Non-Responsibilities
- Detailing specific third-party compiler settings or python package runtime configurations.
- Explaining front-end component framework bindings or client layout structures.

---

## Architectural Flows

The ATLAS architecture divides responsibilities into two distinct, decoupled pipelines: the **Execution Flow** and the **Verification & Commit Flow**.

### 1. Execution Flow (State Generation)
The Execution Flow coordinates the creation of engineering proposals without mutating system state. It flows vertically from user interface triggers down to external providers:

```
        UI / Interface Layer
                 ↓
       Workflow Orchestration
                 ↓
          Stage Executors
                 ↓
       AI Engineering Services
                 ↓
          AI Orchestration
                 ↓
             Provider
```

- **UI / Interface Layer**: The client interface (CLI, API, or IDE adapter) that registers user instructions and initiates actions.
- **Workflow Orchestration** (`WorkflowOrchestrationService`): Drives the pipeline by checking active stages and coordinating generation steps.
- **Stage Executors** (`StageExecutor`): Translates stage-specific requests (e.g. Research, Planning) into engineering calls.
- **AI Engineering Services** (`AIEngineeringService`): Stateless services that assemble context payloads and request proposals.
- **AI Orchestration** (`AIOrchestrationService`): Constructs prompts, applies context strategy compressions, and validates schema parameters.
- **Provider** (`AIProvider`): The dependency inversion boundary wrapping model calls (e.g. `GeminiAIProvider`).

---

### 2. Verification & Commit Flow (State Mutation)
The Verification & Commit Flow processes generated proposals, enforces domain boundaries, and handles atomic filesystem writes:

```
             Proposal
                 ↓
             Validator
                 ↓
            Transformer
                 ↓
           Commit Service
                 ↓
           Domain Services
                 ↓
            Repositories
```

- **Proposal** (`AIProposal`): The stateless data container wrapping LLM-generated drafts (`ai_drafts.py`).
- **Validator** (`ProposalValidator`): Enforces semantic and structural correctness (e.g., verifying references exist).
- **Transformer** (`ProposalTransformer`): Translates verified draft models into calls on domain aggregate services.
- **Commit Service** (`ProposalCommitService`): Orchestrates validation and mutations inside a compensating filesystem transaction (`ProposalCommitUnitOfWork`).
- **Domain Services**: Subsystem services (e.g., `ResearchCaptureService`) that enforce business logic and edit aggregates.
- **Repositories**: Abstract boundaries (`ProjectRepository`, `ArchitectureRepository`) governing aggregate persistence.

---

## Decoupling Strategies & Boundaries

- **Interface-Driven Design**: Services depend on abstractions. For example, `ProposalCommitService` coordinates validation via `ProposalValidator` interfaces without knowing what drafts are being validated.
- **Stateless AI Services**: All prompt building and generation services are completely stateless and hold no references to repository write paths (`save` or `delete`). They can only return proposals.
- **Compensating Transactions**: Since ATLAS runs on the local filesystem, transaction guarantees are achieved using compensating unit-of-work boundaries that back up and restore file contents on failure.

---

## Future Extensions
- A pluggable gateway broker layer allowing stage execution and provider generation to run on distributed remote endpoints.
- Custom external validator plugins integrated directly into the verification chain.
