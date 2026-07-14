# ATLAS Subsystem Extension Guide

## Purpose
This document provides a step-by-step guide for engineers extending the ATLAS platform. It outlines how to introduce a new engineering lifecycle stage, domain model, and repository persistence without violating system boundaries or AI/Engineering Constitutions.

## Responsibilities
- Describe the integration process for new domain models, repositories, and services.
- Detail prompt template construction, validators, and transformers registration.
- Outline workflow state machine modifications and testing requirements.

## Non-Responsibilities
- Writing code templates for unrelated core subsystems.
- Detailing package dependency versions or external runtime deployment scripts.

---

## Extension Steps

To add a new stage to ATLAS, follow this structured progression across the layers:

### 1. Domain Layer
- **Enums**: Register the new stage in `WorkflowStage` and the new proposal type in `ProposalType` inside `engine/domain/enums.py`.
- **Domain Models**: Create a Pydantic model (e.g. in a new file `engine/domain/custom_stage.py`) representing the stage data and snapshot wrapper. Ensure it composes `ArtifactMetadata`.
- **AI Drafts**: Define the Pydantic draft models in `engine/domain/ai_drafts.py` that describe the JSON structures the LLM will generate.
- **Exports**: Expose all new structures in `engine/domain/__init__.py`.

### 2. Repository Layer
- **Interface**: Define the abstract repository interface (e.g., `CustomStageRepository`) in `engine/custom_stage/repository.py` inheriting from `ABC`.
- **Concrete Filesystem Repository**: Create the filesystem-backed implementation in `engine/custom_stage/fs_repository.py` inheriting from the abstract class.
- **Dependency Inversion**: Inject `ProjectRepository` and call `project_repo.get_project_path(project_id)` to resolve file paths dynamically.
- **Rollback Hook**: Implement `delete(project_id)` to ensure the repository supports compensating transaction rollback in the commit service.

### 3. Service Layer
- Create `engine/custom_stage/services.py` with initialization, composition, and summary services.
- These services must interact only with abstract repository contracts.

### 4. AI/Prompting Layer
- **Prompt Template**: Define a template class in `engine/ai/prompts.py` that inherits from `PromptTemplate`. Override `expected_schema` to return the new draft schema.
- **Validator**: Add a `ProposalValidator` subclass in `engine/ai/engineering_services.py` to validate semantic constraints (raising `InvalidProposalException` on errors).
- **Transformer**: Add a `ProposalTransformer` subclass in `engine/ai/engineering_services.py` mapping draft models to calls on the new stage services.
- **Engineering Service**: Create the `CustomStageAIEngineeringService` inheriting from `AIEngineeringService[CustomDraftClass]`.
- **Registration**: Inject the new validator, transformer, and repository into `ProposalCommitService`'s mapping dictionary in `engine/ai/engineering_services.py`.

### 5. Workflow/Orchestration Layer
- **Objectives**: Register the default objectives for the new stage in `DEFAULT_STAGE_OBJECTIVES` inside `engine/workflow/services.py`.
- **Transitions**: Define valid transition paths for the new stage in `WorkflowTransitionService.VALID_TRANSITIONS` state machine registry.
- **Executor**: Create a `StageExecutor` subclass for the new stage in `engine/workflow/orchestration.py`.
- **Registry**: Register the executor mapping in the `StageServiceRegistry`.

### 6. Testing Layer
- Write unit tests for repositories under `tests/custom_stage/test_repository.py`.
- Write unit tests for services under `tests/custom_stage/test_services.py`.
- Add integration tests in `tests/workflow/test_orchestration.py` to verify prompt delegation, validation, commit success, and stage transition flow.

---

## Future Extensions
- Scaffolding CLI tools that dynamically generate boilerplate code for new lifecycle stages using JSON configuration files.
