# ATLAS AI Constitution

## Purpose
This document establishes the ATLAS AI Constitution. It outlines the architectural guardrails, execution boundaries, and safety rules that govern AI interaction, ensuring that AI generation remains secure, stateless, and subservient to human engineering judgment.

## Responsibilities
- Define the core safety and architectural boundaries governing AI orchestrators and providers.
- Explain how the current ATLAS implementation satisfies each constitution rule.
- Document the validation, context assembly, and rollback mechanisms enforcing AI safety.

## Non-Responsibilities
- Describing the mathematical training methods, weights, or neural parameters of external LLMs.
- Outlining rate-limiting configurations or request throttle settings on model hosting servers.

---

## The AI Constitution Rules & Implementations

### Rule 1: Stateless AI Generation
**Requirement**: AI generation must remain completely stateless. No session state or history is tracked by the generation engine, ensuring that outputs are reproducible and determined solely by the input payload.
- *Implementation*: `AIOrchestrationService` and `AIProvider` process queries as self-contained, isolated request-response pairs. All context must be explicitly passed in the `AIRequest` prompt payload.

### Rule 2: No Direct Mutation
**Requirement**: AI components must never have direct write or delete permissions on the repository filesystem. They cannot modify system configurations or codebase files.
- *Implementation*: The `AIOrchestrationService` has no access to repository `.save()` or `.delete()` methods. It can only emit a read-only `AIProposal` holding the uncommitted draft data.

### Rule 3: Deterministic Context Boundary
**Requirement**: The information provided to the AI must be constrained to a verifiable, approved snapshot context. Speculative or unapproved states must be excluded.
- *Implementation*: The `ContextAssemblerService` gathers and freezes only approved snapshots (`ArtifactStatus.APPROVED`) from other subsystems. This prevents dirty or speculative states from entering the generation context.

### Rule 4: Human-in-the-Loop Validation Gate
**Requirement**: AI-generated proposals cannot bypass human judgment. Every change must go through a formal approval gate before persistence.
- *Implementation*: Proposals are generated in `ProposalStatus.DRAFT`. To commit, they must move through `process_review_decision` with a `ProposalDecision.APPROVE` resulting in `ProposalStatus.APPROVED` from a human reviewer.

### Rule 5: Atomic Commit & Fail-Safe Rollback
**Requirement**: Committing an approved proposal must be an atomic operation. If the commit, translation, or validation fails, the workspace must be returned to its exact pre-mutation state.
- *Implementation*: `ProposalCommitService` uses `ProposalCommitUnitOfWork` to create deep backup copies of aggregates before mutations. If an exception occurs, it executes a compensating rollback that restores backups and deletes newly created files.

### Rule 6: Strong Schema Enforcement
**Requirement**: AI responses must conform strictly to predefined Pydantic models. Malformed or unstructured data must be flagged and rejected at the boundary.
- *Implementation*: Prompt templates declare expected JSON schemas using Pydantic's `model_json_schema()`. Response content is immediately parsed and verified using `model_validate`, raising an `InvalidProposalException` on mismatch.

---

## Future Extensions
- Automated static security audits scanning AI-generated code snippets for supply-chain vulnerabilities or insecure packages before human review.
- Token budget limits and cost governance guardrails managed at the provider level.
