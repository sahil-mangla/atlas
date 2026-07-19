# Codebase Structure

**Analysis Date:** 2026-07-19

## Directory Layout

```
atlas/                                      # Project root
├── .atlas/                                  # Workspace storage (created at runtime)
│   └── {project_id}/                        # Per-project storage
│       ├── project.json                     # Project metadata
│       ├── workflow.json                    # Workflow state machine
│       ├── research/                        # Research subsystem storage
│       ├── planning/                        # Planning subsystem storage
│       ├── architecture/                    # Architecture subsystem storage
│       ├── evaluation/                      # Evaluation subsystem storage
│       ├── memory/                          # Memory subsystem storage
│       └── knowledge/                       # Knowledge subsystem storage
│
├── .planning/                               # GSD planning output
│   └── codebase/                            # Codebase analysis documents
│
├── atlas/                                   # Application Platform Layer (public SDK)
│   ├── __init__.py                          # Main entry: create() function
│   ├── _service.py                          # Atlas facade implementation
│   ├── _bootstrap.py                        # Composition root & dependency injection
│   ├── commands.py                          # Command DTOs (input)
│   ├── results.py                           # Result DTOs (output)
│   ├── types.py                             # Enums for public API (ProjectStatus, ProposalStatus, etc.)
│   ├── exceptions.py                        # Application-layer exceptions
│   └── py.typed                             # Type checking marker
│
├── engine/                                  # Core Engine (internal, never imported by clients)
│   ├── __init__.py
│   ├── config.py                            # Settings loading (env vars, .env file)
│   │
│   ├── domain/                              # Domain Models (Pydantic, framework-independent)
│   │   ├── __init__.py
│   │   ├── project.py                       # Project aggregate root
│   │   ├── workflow.py                      # Workflow state machine
│   │   ├── research.py                      # Research domain model
│   │   ├── planning.py                      # Planning domain model
│   │   ├── architecture.py                  # Architecture domain model
│   │   ├── evaluation.py                    # Evaluation domain model
│   │   ├── knowledge.py                     # Knowledge domain model
│   │   ├── memory.py                        # Memory domain model
│   │   ├── ai.py                            # AIProposal, ContextPayload
│   │   ├── ai_drafts.py                     # Draft containers (ResearchProposalDraft, etc.)
│   │   ├── ai_feedback.py                   # ProposalFeedback
│   │   ├── enums.py                         # All shared enums (WorkflowStage, ProjectStatus, etc.)
│   │   ├── traceability.py                  # TraceabilityLink
│   │   ├── metadata.py                      # ArtifactMetadata, ArtifactStatus
│   │   ├── conversation.py                  # Conversation domain model
│   │   ├── review.py                        # ReviewComment model
│   │   ├── engineering_specification.py     # Engineering spec model
│   │   ├── roadmap.py                       # Roadmap model
│   │   ├── vocabulary.py                    # Vocabulary model
│   │   ├── prompt_document.py               # Prompt document metadata
│   │   ├── workspace.py                     # Workspace model
│   │   └── py.typed                         # Type checking marker
│   │
│   ├── project/                             # Project Subsystem
│   │   ├── __init__.py
│   │   ├── fs_repository.py                 # FilesystemProjectRepository
│   │   ├── repository.py                    # ProjectRepository interface
│   │   ├── services.py                      # ProjectCreationService, ProjectLoadingService, etc.
│   │   ├── exceptions.py                    # ProjectException, ProjectNotFoundError, etc.
│   │   └── serializers.py                   # JSON serialization helpers
│   │
│   ├── workflow/                            # Workflow Orchestration Subsystem
│   │   ├── __init__.py
│   │   ├── orchestration.py                 # WorkflowOrchestrationService, StageExecutor, Registry
│   │   ├── fs_repository.py                 # FilesystemWorkflowRepository
│   │   ├── repository.py                    # WorkflowRepository interface
│   │   ├── services.py                      # WorkflowTransitionService, WorkflowReadinessService
│   │   ├── exceptions.py                    # WorkflowException, WorkflowNotFoundException
│   │   └── serializers.py                   # Workflow serialization
│   │
│   ├── research/                            # Research Subsystem
│   │   ├── __init__.py
│   │   ├── fs_repository.py                 # FilesystemResearchRepository
│   │   ├── repository.py                    # ResearchRepository interface
│   │   ├── services.py                      # ResearchInitializationService, ResearchCaptureService, etc.
│   │   ├── exceptions.py                    # ResearchException variants
│   │   └── serializers.py                   # Research serialization
│   │
│   ├── planning/                            # Planning Subsystem
│   │   ├── __init__.py
│   │   ├── fs_repository.py                 # FilesystemPlanningRepository
│   │   ├── repository.py                    # PlanningRepository interface
│   │   ├── services.py                      # PlanningInitializationService, ScopePlanningService, etc.
│   │   ├── exceptions.py                    # PlanningException variants
│   │   └── serializers.py                   # Planning serialization
│   │
│   ├── architecture/                        # Architecture Subsystem
│   │   ├── __init__.py
│   │   ├── fs_repository.py                 # FilesystemArchitectureRepository
│   │   ├── repository.py                    # ArchitectureRepository interface
│   │   ├── services.py                      # ArchitectureInitializationService, ArchitectureCompositionService, etc.
│   │   ├── exceptions.py                    # ArchitectureException variants
│   │   └── serializers.py                   # Architecture serialization
│   │
│   ├── evaluation/                          # Evaluation Subsystem
│   │   ├── __init__.py
│   │   ├── fs_repository.py                 # FilesystemEvaluationRepository
│   │   ├── repository.py                    # EvaluationRepository interface
│   │   ├── services.py                      # EvaluationInitializationService, ReadinessEvaluationService
│   │   ├── exceptions.py                    # EvaluationException variants
│   │   └── serializers.py                   # Evaluation serialization
│   │
│   ├── knowledge/                           # Knowledge Subsystem
│   │   ├── __init__.py
│   │   ├── fs_repository.py                 # FilesystemKnowledgeRepository
│   │   ├── repository.py                    # KnowledgeRepository interface
│   │   ├── services.py                      # KnowledgeApprovalService, KnowledgeRetrievalService, etc.
│   │   ├── orchestration.py                 # KnowledgeOrchestrationService
│   │   ├── extractors.py                    # Knowledge extractors per subsystem
│   │   ├── exceptions.py                    # KnowledgeException variants
│   │   └── serializers.py                   # Knowledge serialization
│   │
│   ├── memory/                              # Memory Subsystem
│   │   ├── __init__.py
│   │   ├── fs_repository.py                 # FilesystemMemoryRepository
│   │   ├── repository.py                    # MemoryRepository interface
│   │   ├── services.py                      # MemoryManagementService
│   │   ├── exceptions.py                    # MemoryException variants
│   │   └── serializers.py                   # Memory serialization
│   │
│   ├── ai/                                  # AI Integration Subsystem
│   │   ├── __init__.py
│   │   ├── config.py                        # ProviderConfig (protocol, endpoint, model, API key)
│   │   ├── provider.py                      # AIProvider base class
│   │   ├── context.py                       # ContextStrategy (IdentityContextStrategy)
│   │   ├── executor.py                      # PromptExecutor (calls provider)
│   │   ├── factory.py                       # ProtocolFactory (resolves provider implementation)
│   │   ├── engineering_services.py          # {Research|Planning|Architecture|Evaluation}AIEngineeringService
│   │   │                                    # + ProposalTransformer & ProposalValidator families
│   │   │                                    # + ProposalCommitService
│   │   ├── services.py                      # AIOrchestrationService, ContextAssemblerService
│   │   ├── fs_repository.py                 # FilesystemProposalRepository
│   │   ├── repository.py                    # ProposalRepository interface
│   │   ├── exceptions.py                    # AIException variants
│   │   ├── serializers.py                   # Proposal serialization
│   │   ├── unit_of_work.py                  # UnitOfWork pattern (if used)
│   │   └── adapters/                        # Provider adapters
│   │       ├── __init__.py
│   │       ├── google_genai.py              # Google Generative AI adapter
│   │       ├── anthropic.py                 # Anthropic adapter (stub/future)
│   │       └── openai.py                    # OpenAI adapter (stub/future)
│   │
│   └── prompt/                              # Prompt Management
│       ├── __init__.py
│       ├── loader.py                        # PromptLoader (loads templates from filesystem)
│       ├── templates/                       # Prompt templates per stage
│       │   ├── research.jinja2
│       │   ├── planning.jinja2
│       │   ├── architecture.jinja2
│       │   └── evaluation.jinja2
│       └── serializers.py                   # Prompt serialization
│
├── clients/                                 # Client Adapters (import only atlas/, never engine/)
│   ├── __init__.py
│   │
│   ├── cli/                                 # CLI Adapter
│   │   ├── __init__.py
│   │   ├── application.py                   # CLIApplication (entry point, command dispatch)
│   │   ├── parser.py                        # Argument parsing (argparse wrapper)
│   │   ├── renderer.py                      # Result rendering (text, colors)
│   │   └── commands.py                      # CLI-specific commands (help, version)
│   │
│   ├── rest/                                # REST API Adapter (stub)
│   │   ├── __init__.py
│   │   └── app.py                           # FastAPI application (future)
│   │
│   ├── mcp/                                 # MCP Adapter (stub)
│   │   ├── __init__.py
│   │   └── server.py                        # MCP server implementation (future)
│   │
│   ├── ide/                                 # IDE Adapter (stub)
│   │   ├── __init__.py
│   │   └── plugin.py                        # IDE plugin entry (future)
│   │
│   ├── desktop/                             # Desktop App Adapter (stub)
│   │   ├── __init__.py
│   │   └── app.py                           # Desktop application (future)
│   │
│   └── common/                              # Shared Client Utilities
│       ├── __init__.py
│       ├── capabilities.py                  # Capability constants per client type
│       ├── rendering.py                     # RenderContext, formatting helpers
│       └── exceptions.py                    # Client-specific exceptions
│
├── presentation/                            # Presentation Layer (Views, Renderers, Orchestration)
│   ├── __init__.py
│   │
│   ├── orchestration/                       # Orchestration models and services
│   │   ├── __init__.py
│   │   └── platform.py                      # Platform coordination layer
│   │
│   ├── renderers/                           # Output rendering strategies
│   │   ├── __init__.py
│   │   ├── base.py                          # BaseRenderer abstract class
│   │   ├── registry.py                      # RendererRegistry (dispatch by type)
│   │   ├── result.py                        # Result rendering (success, error, data)
│   │   └── contract.py                      # Contract/proposal rendering
│   │
│   ├── components/                          # Reusable presentation components
│   │   ├── __init__.py
│   │   └── models.py                        # Component models (Badge, Table, etc.)
│   │
│   ├── views/                               # View models (DTO for presentation)
│   │   ├── __init__.py
│   │   └── models.py                        # WorkflowStatusView, ProjectView, etc.
│   │
│   ├── read_models/                         # Read model builders (domain → view)
│   │   ├── __init__.py
│   │   ├── project.py                       # ProjectReadModel builder
│   │   └── models.py                        # Other read models
│   │
│   └── collectors/                          # Data collection for rendering
│       ├── __init__.py
│       └── collectors.py                    # Collectors per view type
│
├── interfaces/                              # Shared Interface Definitions
│   ├── __init__.py
│   └── repository.py                        # Generic repository interface (if used)
│
├── shared/                                  # Cross-Cutting Utilities
│   ├── __init__.py
│   ├── utils.py                             # Utility functions (date formatting, etc.)
│   ├── validators.py                        # Shared validation logic
│   └── serialization.py                     # JSON/YAML helpers
│
├── tests/                                   # Test Suite (mirrors engine structure)
│   ├── __init__.py
│   ├── conftest.py                          # Pytest fixtures and configuration
│   ├── test_config.py                       # Configuration tests
│   ├── support/                             # Test support files
│   ├── test_atlas/                          # Tests for atlas/ (public SDK)
│   ├── test_clients/                        # Tests for clients/
│   ├── domain/                              # Domain model tests
│   ├── research/                            # Research subsystem tests
│   ├── planning/                            # Planning subsystem tests
│   ├── architecture/                        # Architecture subsystem tests
│   ├── evaluation/                          # Evaluation subsystem tests
│   ├── knowledge/                           # Knowledge subsystem tests
│   ├── memory/                              # Memory subsystem tests
│   ├── ai/                                  # AI subsystem tests
│   ├── workflow/                            # Workflow subsystem tests
│   ├── project/                             # Project subsystem tests
│   └── research/                            # Research subsystem tests
│
├── docs/                                    # Documentation
│   ├── architecture/                        # Architecture decision records
│   ├── decisions/                           # Design decision documents
│   ├── diagrams/                            # Visual diagrams
│   ├── plans/                               # Planning documents
│   └── usage/                               # User guides
│
├── Blueprint/                               # Reference architecture documentation
│   ├── adr/                                 # Architecture Decision Records
│   └── assets/                              # Blueprint assets
│
├── pyproject.toml                           # Project metadata and dependencies
├── pytest.ini (in pyproject.toml)          # Pytest configuration
├── .ruff.toml (configured in pyproject.toml) # Ruff linter settings
├── .mypy.ini (configured in pyproject.toml)  # MyPy type checker settings
├── .pre-commit-config.yaml                  # Pre-commit hook configuration
├── .env.example                             # Environment variables template
├── .gitignore                               # Git exclusions
├── README.md                                # Project overview
└── CHANGELOG.md                             # Release notes
```

## Directory Purposes

**atlas/**
- Purpose: Public Application Platform SDK and facade
- Contains: `Atlas` facade, command DTOs, result DTOs, exceptions, bootstrap logic
- Key files: `__init__.py` (exports `create()`), `_service.py` (facade), `_bootstrap.py` (wiring)
- Access: Client adapters import only from here; never from `engine/`

**engine/domain/**
- Purpose: Strongly-typed ubiquitous language (Pydantic models)
- Contains: All domain aggregates, value objects, enumerations
- Key files: `project.py`, `workflow.py`, `research.py`, `planning.py`, `architecture.py`, `evaluation.py`, `enums.py`
- Isolation: No service imports; only Pydantic and standard library

**engine/{research,planning,architecture,evaluation,workflow,project,knowledge,memory,ai}/**
- Purpose: Independent subsystems with isolated responsibilities
- Pattern: Each has services.py, fs_repository.py, repository.py, exceptions.py
- Key files: `services.py` (business logic), `fs_repository.py` (persistence), `exceptions.py` (domain errors)

**engine/ai/**
- Purpose: AI provider integration and proposal generation
- Contains: Provider adapters, prompt execution, engineering services, transformers, validators
- Key files: `engineering_services.py` (proposal generation), `executor.py` (prompt execution), `adapters/` (provider impls)

**engine/prompt/**
- Purpose: Prompt template management
- Contains: Jinja2 templates loaded at runtime, prompt loader
- Key files: `loader.py`, `templates/{research,planning,architecture,evaluation}.jinja2`

**clients/**
- Purpose: Client adapter implementations (CLI, REST, MCP, IDE, Desktop)
- Pattern: Each client adapts external interface to Atlas SDK DTOs
- Key files: `cli/application.py` (CLI entry), `common/` (shared utilities)
- Constraint: Never imports `engine/`; only `atlas/`

**presentation/**
- Purpose: View layer, renderers, output formatting
- Contains: Renderer registry, result rendering, view models, read models
- Key files: `renderers/`, `views/`, `read_models/`

**tests/**
- Purpose: Comprehensive test coverage
- Pattern: Mirrors `engine/`, `clients/`, `atlas/` structure
- Key files: `conftest.py` (fixtures), test files named `test_*.py` per subsystem
- Config: `pytest.ini` in pyproject.toml; coverage reports in `coverage.xml`

**docs/**
- Purpose: Architecture, decisions, usage documentation
- Contains: ADR (Architecture Decision Records), diagrams, user guides

## Key File Locations

**Entry Points:**
- CLI: `clients/cli/application.py:main()`
- SDK: `atlas/__init__.py:create()`
- Bootstrap: `atlas/_bootstrap.py:_create_platform()`

**Configuration:**
- Settings: `engine/config.py` (loads .env via Pydantic Settings)
- Environment template: `.env.example`

**Core Logic:**
- Atlas facade: `atlas/_service.py`
- Workflow orchestration: `engine/workflow/orchestration.py`
- AI services: `engine/ai/engineering_services.py`
- Proposal commit: `engine/ai/engineering_services.py:ProposalCommitService`

**Testing:**
- Fixtures: `tests/conftest.py`
- Test config: `pyproject.toml:[tool.pytest.ini_options]`

## Naming Conventions

**Files:**
- Python modules: `lowercase_with_underscores.py`
- Subsystem services: `services.py` (all business logic in one file per subsystem)
- Repositories: `fs_repository.py` (implementation), `repository.py` (interface)
- Exceptions: `exceptions.py` (all domain exceptions per subsystem)
- Tests: `test_*.py` or `*_test.py`

**Directories:**
- Packages: `lowercase_with_underscores/`
- Domain models: All in `engine/domain/` (not distributed)
- Subsystem: Singular lowercase (e.g., `engine/research/`, `engine/planning/`)
- Templates: `{stage}.jinja2` (e.g., `research.jinja2`)

**Classes:**
- Services: `{Subsystem}{Operation}Service` (e.g., `ResearchInitializationService`, `PlanningInitializationService`)
- Repositories: `Filesystem{Domain}Repository` (e.g., `FilesystemProjectRepository`)
- Executors: `{Stage}StageExecutor` (e.g., `ResearchStageExecutor`)
- Transformers: `{Stage}ProposalTransformer` (e.g., `ResearchProposalTransformer`)
- Validators: `{Stage}ProposalValidator` (e.g., `ResearchProposalValidator`)
- Exceptions: `{Domain}{Error}Exception` (e.g., `ProjectNotFoundException`, `WorkflowException`)

**Functions/Methods:**
- camelCase not used; PEP 8 `snake_case`
- Service operations: verb-noun pattern (e.g., `initialize_research()`, `get_workflow_status()`)
- Utilities: descriptive (e.g., `load_registry()`, `assemble_context()`)

## Where to Add New Code

**New Feature (e.g., add Reporting Stage):**
1. **Domain models:** `engine/domain/reporting.py` — define `Reporting`, `ReportingStatus`, etc.
2. **Subsystem services:** `engine/reporting/services.py` — create `ReportingInitializationService`, etc.
3. **Repository:** `engine/reporting/fs_repository.py` + `engine/reporting/repository.py`
4. **Exceptions:** `engine/reporting/exceptions.py`
5. **AI integration:** `engine/ai/engineering_services.py` — add `ReportingAIEngineeringService`, `ReportingProposalTransformer`, `ReportingProposalValidator`
6. **Workflow:**
   - Add `REPORTING` to `engine/domain/enums.py:WorkflowStage`
   - Add `ReportingStageExecutor` in `engine/workflow/orchestration.py`
   - Update registry in `atlas/_bootstrap.py:_create_platform()` to include new executor
7. **CLI:** Add subcommand in `clients/cli/parser.py` if needed (auto-dispatched by stage)
8. **Tests:** Create `tests/reporting/` mirroring structure

**New Component/Module (e.g., Caching Layer):**
- Implementation: `engine/caching/cache.py`
- Interface: `engine/caching/cache_provider.py`
- Tests: `tests/caching/test_cache.py`
- Import: Inject into services that need it (not as global singleton)

**Utilities:**
- Shared helpers: `shared/utils.py`
- Serialization: `shared/serialization.py`
- Validation: `shared/validators.py`
- Tests: `tests/support/` for test fixtures and factories

**New Client Adapter:**
1. Create `clients/{adapter_type}/` directory
2. Main entry: `clients/{adapter_type}/application.py`
3. Shared utilities: `clients/common/` (rendering, context, capabilities)
4. Pattern: Parse external input → Command DTO → Atlas facade → Result DTO → Render output
5. Constraint: Never import `engine/`; only `atlas/`

## Special Directories

**`.atlas/`:**
- Purpose: Runtime workspace storage (created on first project creation)
- Structure: Hierarchical by project ID and subsystem
- Example: `.atlas/{project_id}/workflow.json`, `.atlas/{project_id}/research/research.json`
- Generated: Yes (by repositories on save)
- Committed: No (in .gitignore)

**`.planning/`:**
- Purpose: GSD orchestrator output (planning phases, decisions, audits)
- Structure: `codebase/` (analysis docs), `phases/` (phase planning), etc.
- Generated: Yes (by GSD commands)
- Committed: Yes (tracks decisions)

**`tests/support/`:**
- Purpose: Shared test fixtures, factories, mocks
- Contains: Reusable test utilities (not included in coverage)

**`engine/prompt/templates/`:**
- Purpose: Jinja2 prompt templates per stage
- Pattern: One template file per stage; loaded at bootstrap
- Examples: `research.jinja2`, `planning.jinja2`, `architecture.jinja2`, `evaluation.jinja2`

---

*Structure analysis: 2026-07-19*
