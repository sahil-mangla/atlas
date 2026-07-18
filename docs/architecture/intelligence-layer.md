# ATLAS Intelligence Layer

## Purpose
This document details the architecture of the ATLAS Intelligence Layer. It explains the interactions between Prompt Management, stateless AI engineering services, and model providers while demonstrating how the AI Constitution boundaries are enforced.

## Responsibilities
- Define the ownership boundary between prompt definitions and AI prompt execution.
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
                  ├─► Retrieves knowledge via KnowledgeOrchestrationService
                  │
                  ▼
    AIEngineeringService (Stateless coordinator mapping proposals)
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
ContextAssemblerService  AIEngineeringService
                             │
                             ▼
  Prompt Management: PromptLoader → PromptRegistry
                             │
                             ▼
                 AI Runtime: PromptExecutor → AIProvider
```

### 1. Workflow Orchestration
The `WorkflowOrchestrationService` coordinates the active phase. It does not perform LLM calls directly. When executing a stage:
1. It queries `KnowledgeOrchestrationService.retrieve_for_stage` to fetch reviewed project-scoped knowledge.
2. It passes this knowledge context to `ContextAssemblerService` to assemble the context payload.
3. It delegates proposal generation to the stage's executor.
4. After a successful proposal commit, it triggers automatic post-commit extraction via `KnowledgeOrchestrationService.extract_candidate_from_artifact` to capture new candidates for review.

### 2. AI Engineering Services
The `AIEngineeringService` subclasses (e.g. `ResearchAIEngineeringService`) act as stateless coordinators. They:
1. Fetch domain context using the `ContextAssemblerService` (incorporating pre-retrieved knowledge context).
2. Resolve a template from `PromptRegistry` by its draft class.
3. Delegate provider execution and JSON/Pydantic validation to `PromptExecutor`.
4. Construct the `AIProposal` around the resulting typed draft.

### 3. Prompt Management Layer
`engine.prompt` exclusively owns prompt definitions, metadata, versioned prompt
construction, loading, and registration. `PromptLoader` explicitly constructs the
known templates and creates one immutable `PromptRegistry` during bootstrap. The
registry is a passive lookup by draft class; it neither builds nor loads templates.

### 4. AI Runtime
`engine.ai` owns provider-independent execution. Bootstrap constructs and injects
`PromptExecutor` into `AIOrchestrationService`; the executor applies context,
asks the selected template to produce a provider-independent `PromptDocument`,
creates the `AIRequest`, invokes the provider, and validates JSON into the
requested draft type. The runtime does not instantiate, register, or version
prompt templates.

### 5. Protocol Factory
`ProtocolFactory` is a registry-based bootstrap dependency that resolves the
configured protocol adapter (`AIProvider`). It is not consulted during prompt
execution. New protocols are supplied by implementing an adapter and registering
it with the factory while `PromptExecutor` and Prompt Management remain
protocol-agnostic. See [Multi-Protocol AI Runtime](multi-protocol-ai-runtime.md).

---

## Enforcing the AI Constitution

The implementation satisfies the AI Constitution rules through concrete architectural patterns:

- **Stateless AI Boundary**: The `AIOrchestrationService` and `AIProvider` have no connection to repository write operations (`save` or `delete`). They can only output stateless `AIProposal` objects.
- **Deterministic Context Assembly**: The `ContextAssemblerService` enforces context boundaries by querying only *approved* snapshots (`ArtifactStatus.APPROVED`) from other subsystems. Speculative or unapproved states cannot enter the prompt context.
- **Human Review Gate**: AI-generated proposals cannot bypass human judgment. The system requires a formal `process_review_decision` call with `ProposalDecision.APPROVE` to convert a proposal from `DRAFT` to `APPROVED` before any commit can take place.
- **Human Approval for Knowledge Candidates**: AI or system components may propose `KnowledgeCandidate` drafts, but only human actors (`KnowledgeActorType.HUMAN`) can approve and publish them to `PublishedKnowledge`.
- **Immutable Published Knowledge**: Published knowledge entries are frozen (`frozen=True`) and content cannot be mutated in place. All changes must go through versioning and superseding links.
- **Knowledge vs Memory Distinction**: `Memory` governs dialog logs and contextual conversational memory, while `Knowledge` represents verified, curated engineering standards, patterns, and principles.
- **Schema Validation**: The system uses Pydantic validation (`model_validate`) to parse LLM outputs. This prevents invalid data structures from corrupting the domain layer.

---

## Future Extensions
- Multimodal context processing allowing developer screenshots and layout frames to be analyzed during generation.
- Semantic context search that dynamically selects memory entries and citations based on instruction embeddings.
