# ATLAS Engineering Constitution

## Purpose
This document establishes the fundamental engineering principles and coding standards that govern all designs, modifications, and reviews within the ATLAS platform. It outlines how these principles are structurally enforced to ensure long-term codebase health.

## Responsibilities
- Establish the code quality standards and behavioral expectations for ATLAS contributions.
- Detail the core engineering philosophy (e.g. Architecture Before Implementation).
- Provide the audit checklist used during human review and validation phases.

## Non-Responsibilities
- Listing specific external security credentials, server endpoints, or hosting policies.
- Prescribing specific package release numbers or environment deployment runbooks.

---

## Core Engineering Philosophy

### 1. Architecture Before Implementation
No codebase changes or features may be introduced without an approved design blueprint in the workspace. Implementation is treated as the logical consequence of a complete, verified design.

### 2. Simplicity Over Cleverness
We prioritize simple, flat, and readable code structures. Speculative abstractions, premature optimizations, and complex programming patterns are prohibited in favor of clear, self-documenting execution paths.

### 3. Single Responsibility
Every module, class, service, and function must have exactly one clearly defined responsibility. Components should only have a single reason to change; large or multi-faceted components must be refactored.

### 4. Explicit Over Implicit
All dependencies, configurations, and state transitions must be explicitly declared. Hidden side-effects, implicit global variables, and magic parameters are not permitted.

### 5. Modular by Design
The system consists of decoupled subsystems communicating across stable, interface-driven boundaries. Modifying the internal logic of one subsystem must not cause cascading side effects.

### 6. Human-Centered Engineering
AI agents are utilized to automate tasks and assist in implementation, but humans retain absolute ownership of the design. Critical engineering judgment remains with the developer.

---

## Code Quality Standards & Enforcement

ATLAS enforces coding rules through static analysis checks, type validation layers, and automated verification:

- **Type Hints Required**: All signatures—including parameters, variables, and return types—must be fully typed. Dynamic typing is prohibited.
- **Public Interfaces Documented**: Public-facing classes and functions must include descriptive docstrings detailing inputs, outputs, exceptions, and side effects.
- **Clear & Concise Code**: Code standard gates verify that functions perform single logical tasks, avoid duplicate logic, and minimize nested branches (preferring guard clauses).
- **Review Checklist**: Every contribution must satisfy the following checklist before merge:
  - *Correctness*: Code handles edge cases and failures gracefully.
  - *Readability*: Code flow is clear and quickly understandable.
  - *Modularity*: Subsystem boundaries and interfaces are strictly respected.
  - *Testability*: Appropriate unit, integration, or contract tests validate the execution.

---

## Future Extensions
- Automated Abstract Syntax Tree (AST) validation in the evaluation pipeline to flag functions exceeding nesting depth or lines-of-code thresholds.
- Pre-commit gating that blocks project commits unless Ruff, mypy, and pytest verifications pass cleanly.
