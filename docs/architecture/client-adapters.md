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

## Future Adapters

The following adapters are scaffolded and reserved for future extension:
- **MCP**: Model Context Protocol integration.
- **IDE**: Extension host wrappers for VS Code or JetBrains.
- **REST**: Over-the-wire HTTP APIs.
- **Desktop**: Local GUI client integrations.
