# ATLAS System Overview

## Purpose
This document provides a high-level overview of the ATLAS system architecture. It outlines the core product vision, explains the philosophy of human-centered AI engineering, and defines the responsibilities, inputs, outputs, and relationships of every major subsystem in the ATLAS platform.

## Responsibilities
- Serve as the entry point to understanding the ATLAS system topology.
- Define boundaries and clear areas of concern for all 11 core subsystems.
- Articulate the human-centered automation paradigm where AI acts as an assistant rather than an authority.

## Non-Responsibilities
- Describing concrete execution code or internal package helper utilities.
- Outlining user interface components or client-specific adapters (e.g. IDE extensions).

---

## Project Vision & Philosophy

### Vision
ATLAS is an AI-native engineering operating system that transforms ideas into production-ready software through structured research, architecture, planning, implementation, verification, and persistent project intelligence.

### AI as Assistant, Not Authority
In ATLAS, AI agents are tools utilized to assist in implementation, speed up execution, and automate repetitive tasks. However, humans retain absolute ownership of the architecture, technical decisions, and strategic direction of the system. The system design ensures that the AI cannot mutate the repository without human review and explicit approval.

---

## Subsystem Reference

### 0. Application Platform Layer (Public SDK)
- **Purpose**: Serves as the single, canonical public interface (`atlas/`) for all external clients (CLI, IDE, Web, etc.). Enforces boundary rules, maps internal exceptions, and implements the Command-Result pattern.
- **Inputs**: Immutable Command DTOs from first-party and third-party clients.
- **Outputs**: Pure Result DTOs reflecting platform state or operation outcomes.
- **Collaborators**: Coordinates across all internal engine subsystems to fulfill client requests.

### 1. Project Subsystem
- **Purpose**: Acts as the orchestrator and entry point for the ATLAS application, managing workspace lifecycle and global states.
- **Inputs**: User requests to create, load, pause, resume, or archive projects; context updates from child subsystems.
- **Outputs**: Initialized workspace contexts, project status metadata, and session status logs.
- **Collaborators**: Collaborates with all subsystems to coordinate lifecycle transitions and progress tracking.

### 2. Memory Subsystem
- **Purpose**: Serves as the central repository for persistent context, historical logs, and conversation history.
- **Inputs**: Dialogue entries, tool executions, and design outcomes from other subsystems.
- **Outputs**: Historical query results, chat transcripts, and semantic context definitions.
- **Collaborators**: Supports all subsystems by saving and retrieving session contexts without directing their logic.

### 3. Workflow Subsystem
- **Purpose**: Enforces stage transition rules and tracks stage-level checklist objectives.
- **Inputs**: Transition requests, stage completion signals, and objective completions.
- **Outputs**: Current workflow stage, active stage objectives, transition history logs, and transition approvals.
- **Collaborators**: Project Subsystem (for status alignment) and Workflow Orchestration (for state advancement).

### 4. Research Subsystem
- **Purpose**: Explores, structures, and documents knowledge about problem domains and technical requirements.
- **Inputs**: Problem definitions, external literature searches, and user research directives.
- **Outputs**: Research summaries, evidence references, citation logs, and knowledge gap briefs.
- **Collaborators**: Memory Subsystem (for persistence) and Architecture Subsystem (for design input).

### 5. Planning Subsystem
- **Purpose**: Decomposes project scope and requirement criteria into milestone-driven task roadmaps.
- **Inputs**: Core scoping statements, requirement checklists, and task completion updates.
- **Outputs**: Milestone logs, epic groupings, task lists, subtask arrays, and dependency maps.
- **Collaborators**: Workflow Subsystem (for tracking stage tasks) and Architecture Subsystem (to align with components).

### 6. Engineering Design Language (EDL)
- **Purpose**: Defines standard domain-level entities for traceability, metadata, and reviews.
- **Inputs**: Object definitions requiring metadata encapsulation or upstream linkage.
- **Outputs**: Standardized schemas for `ArtifactMetadata`, `TraceabilityLink`, and `EngineeringReview`.
- **Collaborators**: Serves as a cross-cutting language imported by all domain aggregates (`engine/domain/`).

### 7. Architecture Subsystem
- **Purpose**: Defines technical system designs, component boundaries, and Architectural Decision Records (ADRs).
- **Inputs**: Research findings, design choices, and requirement constraints.
- **Outputs**: Component specifications, interface contracts, data models, and active ADR logs.
- **Collaborators**: Research Subsystem (uses findings) and Evaluation Subsystem (supplies design benchmarks).

### 8. Evaluation Subsystem
- **Purpose**: Reviews code modifications and validates functional compliance against design rules.
- **Inputs**: Code implementations, architecture contracts, and target engineering specifications.
- **Outputs**: Code quality reviews, compliance reports, and readiness decisions.
- **Collaborators**: Architecture Subsystem (verifies designs) and AI Integration (receives agent output).

### 9. AI Integration Subsystem
- **Purpose**: Manages communication, API formatting, and capability discovery for LLM providers.
- **Inputs**: Prompt templates, context payloads, and tool schema lists.
- **Outputs**: Formatted LLM requests and normalized provider-agnostic response schemas.
- **Collaborators**: Connects AI Orchestration with external model providers (e.g. Gemini).

### 10. AI Engineering Services
- **Purpose**: Provides stateless services for generating, validating, and committing proposal drafts.
- **Inputs**: User instructions, project identifiers, and approved snapshots.
- **Outputs**: Strongly typed proposal drafts and commit results.
- **Collaborators**: Repositories, Domain Services, and AI Orchestration.

### 11. Workflow Orchestration
- **Purpose**: Orchestrates the sequential pipeline of proposal generation, validation, and human-in-the-loop sign-off.
- **Inputs**: User instructions and human review decisions.
- **Outputs**: Completed proposal commits, readiness audits, and automated stage transitions.
- **Collaborators**: Workflow Subsystem, AI Engineering Services, and Commit Services.

### 12. Client Adapter Layer
- **Purpose**: Translates external execution environments (CLI, MCP, IDE, REST) into actions on the public Atlas SDK. Provides presentation formatting and progress tracking.
- **Inputs**: Raw external interactions (e.g., `sys.argv`, JSON-RPC payloads).
- **Outputs**: Environment-specific formatted output (e.g., ANSI terminal strings, structured JSON responses).
- **Collaborators**: Depends exclusively on the Application Platform Layer (Atlas SDK) and shared presentation utilities.

---

## Future Extensions
- Support for multi-project workspaces where a parent project coordinates dependencies across child repositories.
- Integrated performance profiling and security vulnerability scanning subsystems.
