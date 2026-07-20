# Client Adapter Layer

## Purpose
This document outlines the architecture, constraints, and responsibilities of the Client Adapter Layer within the ATLAS engineering platform.

## Overview
The Client Adapter Layer provides presentation and transport bindings to external execution environments (CLI, MCP, IDE, REST, Desktop). It wraps the internal capabilities of the engine, making them accessible to humans or external agent systems without exposing internal states or dependencies.

The adapters exist solely to translate external interactions into the public Atlas SDK. They never own engineering logic or bypass the SDK boundary.

## Core Principles

1. **Stateless Adapaters**: Adapters hold no engineering state.
2. **Public Boundary**: Adapters interact exclusively with the `atlas` package.
3. **No Engine Imports**: Adapters must never import from the `engine` subsystem.
4. **Presentation Only**: Adapters manage how data is displayed and transported. All domain logic stays in the engine.
5. **Unified Error Handling**: Adapters only catch and format `ApplicationError` variants.

## Adapter Lifecycle

Every client command follows a strict lifecycle:

```text
Client (Terminal, Web, IDE)
↓
Adapter Parser / Router (Creates Command DTO)
↓
Atlas SDK (Performs operation)
↓
Result DTO (Returned to Adapter)
↓
Adapter Renderer (Formats output)
↓
Client (Display)
```

## Shared Capabilities

To avoid duplicated formatting logic across similar text-based adapters, the `clients/common` module provides shared presentation utilities:

- **Formatting**: Plain-text tabular rendering, lists, markdown wrapping, tree rendering.
- **Progress**: CLI-agnostic progress bar math and tracking objects.
- **Rendering**: Base contextual rendering abstractions.
- **Capabilities**: Standardized capability definitions (`AdapterCapabilities`).

## Implemented Adapters

### CLI Adapter
The CLI is the primary testing and interaction interface. It implements parsing via flat `sys.argv` arrays mapped directly to Command DTOs. Its renderer uses `clients/common` to generate rich terminal output.

Since Phase 15, `CLIApplication` also declares an `AdapterContext` (`atlas.adapters.protocol`) and exposes `context` / `negotiate()`, structurally satisfying the `PlatformAdapter` protocol -- see below. Its dispatch loop is unchanged: it continues calling named `Atlas` methods directly rather than `Atlas.handle()`, since it is an in-process caller (see Usage Policy below).

## Future Adapters

The following adapters are scaffolded and reserved for future extension:
- **MCP**: Model Context Protocol integration.
- **IDE**: Extension host wrappers for VS Code or JetBrains.
- **REST**: Over-the-wire HTTP APIs.
- **Desktop**: Local GUI client integrations.

Any adapter built against these stubs in a future phase is expected to implement `PlatformAdapter` (below) and call through `Atlas.handle()` rather than named methods.

---

## Phase 15: Platform Adapter Boundary

`atlas.adapters.protocol.PlatformAdapter` is the structural contract (a `@runtime_checkable` `Protocol`, not a base class) any client adapter satisfies:

```python
class PlatformAdapter(Protocol):
    @property
    def context(self) -> AdapterContext: ...
    def negotiate(self, atlas: Atlas) -> PlatformCapabilityManifest: ...
```

- `AdapterContext` (`kind`, `name`, `version`) is the identity a client presents to the platform. `AdapterKind` covers `CLI`, `IDE`, `MCP`, `AI`, `REST`, `DESKTOP`.
- `PlatformCapabilityManifest` is what the platform tells an adapter it exposes -- `capabilities: tuple[CapabilityName, ...]`, strongly typed via the `CapabilityName` enum (`atlas.capabilities.base`), never raw strings. The manifest is static in Phase 15 (all five capabilities always present) -- the seam for future capability-based authorization scoping.

### Usage Policy: Named Methods vs. `Atlas.handle()`

Named `Atlas` methods remain **permanently supported** for the CLI adapter -- they are not deprecated. `Atlas.handle(RequestEnvelope) -> ResponseEnvelope` is the **preferred** (not enforced) entry point for MCP, REST, IDE integrations, AI agents, and any future out-of-process or protocol-driven adapter, since those callers need the envelope's request id, API version, and adapter identity for serialization, logging, tracing, and version negotiation that an in-process caller does not need.

See [Platform Layer](platform-layer.md) for the full design.
