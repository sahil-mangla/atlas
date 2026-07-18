# Engineering Knowledge Layer

Phase 13 introduces `engine/knowledge/` as an independent subsystem for project-scoped engineering knowledge.

Workflow communicates with knowledge only through `KnowledgeOrchestrationService`. The AI and prompt runtimes do not import the knowledge subsystem. Retrieved knowledge is passed to AI only through immutable `ContextPayload`.

Candidates may come from human submissions, approved-artifact extraction, or imports. They are deduplicated and remain pending until human review. Approval publishes immutable knowledge; rejection and withdrawal are terminal candidate states. Published entries may be superseded or deprecated.

`KnowledgeCandidateService`, `KnowledgeApprovalService`, `KnowledgeLifecycleService`, `KnowledgeRetrievalService`, and `KnowledgeDeduplicationService` own their respective operations. `KnowledgeOrchestrationService` is the external boundary.

`KnowledgeRepository` and `FilesystemKnowledgeRepository` persist a `KnowledgePersistenceDocument` at `.atlas/knowledge.json`. Phase 13 uses Pydantic model JSON serialization directly in this repository and does not add a knowledge-specific serializer abstraction.

Workflow retrieves active knowledge before generation, passes it to context assembly, and supplies the immutable `ContextPayload` to AI. Successful proposal commits trigger post-commit candidate extraction.
