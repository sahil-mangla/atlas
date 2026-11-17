# ATLAS Service Contracts

In a modular software architecture, subsystems must communicate through well-defined contracts rather than depending on each other's internal implementation details. Establishing formal, conceptual contracts ensures that subsystems remain decoupled and independent. It guarantees that any internal changes, optimization, or implementation refactoring within a subsystem will not break the behaviors of collaborating systems, thereby preserving overall platform stability and ease of testing.

---

# Contract Principles

All service interactions within ATLAS are governed by the following core principles:

- **Clear Responsibilities**: Every subsystem owns its own domain objects and execution logic. No subsystem is permitted to perform tasks or mutate data that conceptually belongs to another.
- **Explicit Collaboration**: Subsystems request services from one another through clearly defined contracts. They must never bypass boundaries or access another subsystem's internal implementations or private storage models.
- **Low Coupling**: The dependencies between subsystems are minimized. A change to the internal execution flow of one subsystem must not require changes across the other subsystems.
- **Stable Interfaces**: Service contracts must remain stable and backward-compatible. Technical changes, updates, or backend optimizations should be insulated behind these contracts to avoid disrupting consumer systems.

---

# System Contracts

## Project System

### Provides
- **Project Lifecycle**: Operations to initialize, load, pause, resume, and archive projects.
- **Project Status**: System-level completion metrics and global execution metadata.
- **Project Identity**: Authorization boundaries, metadata, and workspace configuration limits.

### Consumes
- **Research**: To align project goals with technical investigations.
- **Planning**: To retrieve milestone completion percentages and task timelines.
- **Workflow**: To verify workflow prerequisites before lifecycle transitions.
- **Memory**: To save and restore project states and configuration logs.
- **Evaluation**: To determine if the project has met the quality criteria for completion.

---

## Research System

### Provides
- **Research Findings**: Structured data containing analyzed domain facts and technical options.
- **Literature Summaries**: Outlines and digests of retrieved papers, guides, and external citations.
- **Research Gaps**: Lists of unresolved uncertainties and unverified design assumptions.

### Consumes
- **Project**: To acquire the target problem boundaries and requirements context.
- **Memory**: To record, search, and recall historical research findings and references.

---

## Planning System

### Provides
- **Roadmaps**: Structured schedules of milestones and prioritized task lists.
- **Milestones**: Target release states containing verified capabilities.
- **Implementation Plans**: Detailed task descriptions and dependencies mapping.

### Consumes
- **Project**: To report roadmap and task completion status metrics.
- **Research**: To integrate technical findings into task parameters.
- **Architecture**: To import the structural components and interfaces that need scheduling.

---

## Architecture System

### Provides
- **Technical Designs**: Blueprint configurations defining subsystems, interfaces, and data models.
- **Architecture Decisions**: Formal Architectural Decision Records (ADRs) detailing design trade-offs.
- **Design Validation**: Validation rules to verify code files conform to the architectural blueprints.

### Consumes
- **Research**: To evaluate design options against researched facts and benchmarks.
- **Planning**: To map design boundaries to scheduled implementation packages.
- **Memory**: To log design history, versions, and decision transcripts.

---

## Workflow System

### Provides
- **Workflow Progress**: The active workflow stage, completed checklists, and pending tasks.
- **Stage Guidance**: Contextual guidance recommending the next logical engineering action.
- **Engineering Lifecycle**: State transitions and boundary validations across lifecycle stages.

### Consumes
- **Project**: To align the overall workspace state with lifecycle milestones.
- **Planning**: To verify that the tasks associated with a stage are planned and prioritized.
- **Architecture**: To import design boundaries and validation rules.
- **Evaluation**: To confirm that implemented changes have passed all reviews before advancing.

---

## Memory System

### Provides
- **Engineering Knowledge**: Contextual logs, decision logs, and conversation histories.
- **Historical Context**: Historic session states and configuration parameters for workspace restoration.
- **Project Memory**: Global, long-term archival storage of all project metadata.

### Consumes
- Consumes and structures knowledge inputs, configurations, state changes, and history from every subsystem.
- *Memory operates as a cross-cutting subsystem. It supports all other subsystems by providing context and persistence, but it does not direct their logic, enforce workflows, or own their respective domain responsibilities.*

---

## Evaluation System

### Provides
- **Quality Assessments**: Audit reports detailing code readability, nesting depth, and compliance metrics.
- **Engineering Validation**: Verification checks confirming implementation alignment with specifications.
- **Review Outcomes**: Verification passes, warnings, or blocking defects.

### Consumes
- **Architecture**: To acquire design contracts, schemas, and structural boundaries.
- **Planning**: To check that review tasks align with roadmap schedules.
- **Workflow**: To verify that the project is in the appropriate evaluation stage.

---

# Collaboration Rules

To maintain absolute architectural boundaries, all subsystems must strictly adhere to the following collaboration rules:
- **Encapsulation**: A subsystem has sole authority over its data. Other subsystems must request modifications through explicit contracts rather than direct manipulation.
- **Request-Response Flow**: Collaboration must occur through defined request and notification patterns. One subsystem requests a service; the receiving subsystem processes the request and returns a structured response.
- **No Direct Modification**: A subsystem must never modify another subsystem's internal state, private workspace files, or configurations directly.
- **Contract Enforcement**: All communication across subsystem boundaries is strictly governed by the contracts established in this document.

---

# Dependency Direction

Dependencies between subsystems must point toward stable, abstract interfaces rather than internal, concrete execution layers. Under this model:
- Subsystems with highly specific execution rules (e.g., **Workflow** or **Evaluation**) depend on stable configurations provided by orchestrators (e.g., **Project** or **Architecture**).
- No subsystem should depend on the private utilities, helper structures, or local data formats of another.
- By ensuring that dependencies flow toward stable service descriptions, we insulate the codebase from cascading changes.

---

# Future Evolution

New subsystems (e.g., notification systems, external gateway adapters) may be introduced into the ATLAS ecosystem. Any new system must establish clear, well-defined service contracts, declare its inputs and outputs, and respect the boundaries of existing subsystems.

---

# Closing Statement

Service contracts preserve modularity, maintainability, and long-term architectural stability across ATLAS. By formalizing these boundary lines, we guarantee that the platform can grow in capabilities while remaining simple to understand, test, and maintain.
