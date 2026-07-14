# ATLAS Intelligence Layer

## Purpose
This document details the architecture of the ATLAS Intelligence Layer. It explains the interactions between workflow orchestration, stateless AI engineering services, and model providers while demonstrating how the AI Constitution boundaries are enforced.

## Responsibilities
- Define the structural boundaries between AI prompt generation and repository state mutations.
- Detail the coordination of `AI Integration`, `AI Engineering Services`, and `Workflow Orchestration`.
- Document how context is assembled and how provider responses are parsed.

## Non-Responsibilities
- Listing the specific natural language text templates used for prompt construction.
- Detailing host endpoints, network parameters, or authentication keys for external model providers.

---

## Intelligence Layer Architecture

The intelligence layer maps user instructions and domain context to strongly typed proposal drafts through three major components:

```
    WorkflowOrchestrationService (Stateful orchestrator driving stages)
                  │
                  ▼
    AIEngineeringService (Stateless coordinator mapping proposals)
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
ContextAssemblerService  AIOrchestrationService (Prompt & Strategy builder)
                            │
                            ▼
                         AIProvider (Gemini Adapter)
```

### 1. Workflow Orchestration
The `WorkflowOrchestrationService` coordinates the active phase. It does not perform LLM calls directly; instead, it delegates to the stage's executor to trigger proposal generation, and processes human review decisions via `process_review_decision`.

### 2. AI Engineering Services
The `AIEngineeringService` subclasses (e.g. `ResearchAIEngineeringService`) act as stateless coordinators. They:
1. Fetch domain context using the `ContextAssemblerService`.
2. Submit the context and prompts to the `AIOrchestrationService`.
3. Map the raw JSON string content back to strongly typed Pydantic models (e.g. `PlanningProposalDraft`).

### 3. AI Orchestration
The `AIOrchestrationService` builds prompt templates and applies context strategies (e.g. identity context mappings) to create `AIRequest` objects. It queries the `AIProvider` to receive raw, schema-enforced JSON content.

---

## Enforcing the AI Constitution

The implementation satisfies the AI Constitution rules through concrete architectural patterns:

- **Stateless AI Boundary**: The `AIOrchestrationService` and `AIProvider` have no connection to repository write operations (`save` or `delete`). They can only output stateless `AIProposal` objects.
- **Deterministic Context Assembly**: The `ContextAssemblerService` enforces context boundaries by querying only *approved* snapshots (`ArtifactStatus.APPROVED`) from other subsystems. Speculative or unapproved states cannot enter the prompt context.
- **Human Review Gate**: AI-generated proposals cannot bypass human judgment. The system requires a formal `process_review_decision` call with `ProposalDecision.APPROVE` to convert a proposal from `DRAFT` to `APPROVED` before any commit can take place.
- **Schema Validation**: The system uses Pydantic validation (`model_validate`) to parse LLM outputs. This prevents invalid data structures from corrupting the domain layer.

---

## Future Extensions
- Multimodal context processing allowing developer screenshots and layout frames to be analyzed during generation.
- Semantic context search that dynamically selects memory entries and citations based on instruction embeddings.
