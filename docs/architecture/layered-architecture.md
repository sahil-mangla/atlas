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
The Execution Flow coordinates the creation of engineering proposals without mutating system state. It flows vertically from external clients down to external AI providers:

```
          External Clients (Terminal, IDE, Web)
                  ↓
          Client Adapter Layer (CLI, MCP, etc.)
                  ↓
       Application Platform Layer (Atlas SDK)
                  ↓
       Workflow Orchestration
                  ↓
          Stage Executors
                  ↓
          AI Engineering Services
                  ↓
        Prompt Management (Registry)
                  ↓
          AI Orchestration
                  ↓
          Prompt Executor
                  ↓
             AI Provider
```

- **External Clients**: First-party and third-party UI/Interface clients that initiate actions.
- **Client Adapter Layer**: Translates raw client inputs (e.g. `argv`) into Command DTOs and handles presentation-specific rendering.
- **Application Platform Layer** (`Atlas` Facade): The public boundary that enforces the Command-Result pattern, mapping exceptions and hiding internal engine complexity.
- **Workflow Orchestration** (`WorkflowOrchestrationService`): Drives the pipeline by checking active stages and coordinating generation steps.
- **Stage Executors** (`StageExecutor`): Translates stage-specific requests (e.g. Research, Planning) into engineering calls.
- **AI Engineering Services** (`AIEngineeringService`): Stateless services that assemble context payloads and request proposals.
- **Prompt Management** (`PromptLoader`, `PromptRegistry`): Owns immutable, versioned prompt definitions and exposes passive template lookup.
- **AI Orchestration** (`AIOrchestrationService`): Receives injected prompt runtime dependencies and coordinates their use for engineering services.
- **Prompt Executor** (`PromptExecutor`): Applies context strategy, executes a resolved template, invokes the provider, and validates the response schema.
- **AI Provider** (`AIProvider`): The dependency inversion boundary wrapping model calls. Protocol adapters implement this interface. `ProtocolFactory` resolves the selected protocol only during bootstrap.

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
- **Knowledge Layer Separation**: The Engineering Knowledge Layer (`engine/knowledge`) is strictly separated from the AI Runtime (`engine/ai`) and Memory (`engine/memory`). Retrieval is orchestrated by Workflow before generation, while `ContextAssemblerService` remains a passive serializer. Published knowledge is immutable and guarded at the persistence boundary.

---

## Future Extensions
- A pluggable gateway broker layer allowing stage execution and provider generation to run on distributed remote endpoints.
- Custom external validator plugins integrated directly into the verification chain.
