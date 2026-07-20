# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - Phase 15: Platform Layer

### Added
- `atlas/capabilities/`: Capability Layer decomposing the `Atlas` facade into five thin delegation classes (`ProjectCapability`, `WorkflowCapability`, `WorkflowExecutionCapability`, `KnowledgeCapability`, `PresentationCapability`), each a pure relocation of pre-existing `Atlas` method logic.
- `atlas/contracts/`: versioned `RequestEnvelope`/`ResponseEnvelope`, the `PlatformErrorCode`/`ErrorEnvelope` error contract with an explicit, completeness-tested mapping from every `ApplicationError` subclass, and `PLATFORM_API_VERSION`/`SCHEMA_VERSION`/`is_compatible()`.
- `atlas/adapters/`: the structural `PlatformAdapter` protocol, `AdapterContext`, `AdapterKind`, and `PlatformCapabilityManifest`.
- `Atlas.handle(RequestEnvelope) -> ResponseEnvelope`: the preferred uniform dispatch entry point for out-of-process/protocol clients (MCP, REST, IDE, AI agents); named `Atlas` methods remain permanently supported for the CLI, tests, and in-process consumers.
- CLI adapter retrofit: `AdapterContext`, `context` property, `negotiate()` -- proves structural `PlatformAdapter` conformance without changing the CLI's dispatch loop.
- New docs: `docs/architecture/platform-layer.md`, `docs/decisions/adr-004-platform-capability-contract-layer.md`, `docs/diagrams/platform-request-dispatch.md`.
- New tests: `tests/contracts/`, `tests/adapters/`, `tests/test_atlas/test_platform_handle.py`, `tests/architecture/test_platform_boundaries.py`.

### Notes
- Zero changes to `engine/*` or `presentation/*`; zero changes to `Command`/`Result` DTO shapes; zero behavior changes to any existing `Atlas` method.

## [0.1.0] - 2026-07-12

### Added
- Initialized repository structure.
- Defined product identity and tagline.
- Established engineering blueprint file hierarchy.
- Completed the vision document `Blueprint/01-vision.md`.
