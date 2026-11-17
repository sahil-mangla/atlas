# ATLAS Engineering Constitution

> This document defines the engineering principles that govern every architectural decision, implementation, and review within ATLAS.

---

# Purpose

This document establishes the fundamental engineering standards and practices for ATLAS. It exists to guarantee that the codebase and design remain maintainable, understandable, scalable, modular, and consistent over time, regardless of the size of the project or the individuals or agents contributing to it. By establishing these rules, we ensure that technical debt is minimized and the system remains stable and adaptable to future requirements.

---

# Core Philosophy

## Architecture Before Implementation

Implementation follows architecture; architecture never follows implementation. No feature or system behavior should be introduced without an approved design blueprint. Developers and agents must map out the system boundaries, API contracts, and data structures before writing executable code.

## Simplicity Over Cleverness

We prioritize the simplest technical solution that fully satisfies the system requirements. Unnecessary abstractions, speculative optimization, and over-engineering degrade readability and introduce hidden bugs. Clear, self-documenting code is always preferred over complex or clever patterns.

## Single Responsibility

Every subsystem, package, module, class, and function must have exactly one clearly defined responsibility. Overlapping behaviors or blurred boundaries lead to fragile code. If a component must change for more than one reason, it should be refactored into smaller, cohesive units.

## Explicit Over Implicit

System behavior must be obvious, readable, and predictable. Magic values, hidden side effects, and implicit behaviors are prohibited. Configuration and dependencies should be explicitly declared to avoid unexpected coupling and to make execution paths easy to trace.

## Modular by Design

The platform must be built as a set of decoupled, independent components. Subsystems communicate across clean, well-defined boundaries. Modifying the internal logic of one module must not trigger cascading changes across unrelated parts of the codebase.

## Human-Centered Engineering

AI agents are tools utilized to assist in implementation, speed up execution, and automate repetitive tasks. However, humans retain absolute ownership of the architecture, technical decisions, and strategic direction of the system. Engineering judgment remains with the developer.

---

# Engineering Principles

## Separation of Concerns
This principle separates the system into distinct sections, where each section addresses a separate concern (e.g., domain logic, presentation, data persistence, external communication). It prevents tightly coupled spaghetti code, allowing developers to modify or swap out subsystems with minimal disruption.

## Dependency Injection
Components should not instantiate their dependencies internally. Instead, dependencies must be injected from the outside, typically through constructor parameters. This practice keeps code decoupled, makes dependency graphs explicit, and simplifies module replacement and testing.

## Composition over Inheritance
We prefer composition (combining simple objects to build complex behavior) over inheritance hierarchies. Composition provides greater runtime flexibility, avoids deep class hierarchies that are difficult to refactor, and minimizes the risk of breaking subclasses when base classes are modified.

## Strong Typing
The system relies on strong type declarations for interfaces, parameters, return types, and data models. Strong typing acts as compile-time or static verification, catching structural mismatches early and clarifying expectations for developers and agents reading the code.

## Interface-Driven Design
Code should depend on abstractions (interfaces or abstract definitions) rather than concrete implementations. This decouples the caller from the execution details, allowing multiple implementations to be substituted seamlessly without affecting dependent modules.

## Testability
Code must be designed from the outset to be easily verifiable. Components that rely on side effects, clock times, database states, or external networks must be structured to allow clean mocking or isolation. A feature cannot be considered stable without comprehensive automated verification.

## Documentation
Documentation is code. Every architectural decision, public interface, configuration schema, and system component must be thoroughly documented. Up-to-date documentation reduces cognitive load and ensures that new engineers or agents can build context immediately.

---

# Code Standards

To maintain code readability and reduce technical debt, all contributions must adhere to the following standards:

- **Clear Naming**: Variable, function, and class names must explicitly describe their purpose or content. Avoid ambiguous abbreviations or generic names.
- **Small Functions**: Functions should perform a single logical task. If a function contains multiple steps or branches, extract them into smaller, descriptive helper functions.
- **Small Modules**: Keep files and modules focused on a single logical group of behaviors. Large, monolithic files should be broken down into cohesive structures.
- **Descriptive Variables**: Avoid reuse of variables for different purposes. Use intermediate variables with descriptive names to clarify complex expressions.
- **No Duplicated Logic**: Extract repeated logic into shared utility modules or common abstractions to prevent divergence and simplify maintenance.
- **Avoid Deep Nesting**: Minimize nested branches, loops, and conditional statements. Use guard clauses to exit early and keep the main execution path flat.
- **Type Hints Required**: All signatures—including parameters and return types—must be fully typed. Avoid dynamic typing fallback options unless strictly necessary.
- **Public Interfaces Documented**: All public-facing modules, classes, and functions must be accompanied by docstrings explaining their inputs, outputs, exceptions, and side effects.

---

# Documentation Standards

- **Design First**: Architectural decisions, API contracts, database schemas, and interface updates must be documented and reviewed *before* implementation begins.
- **Continuous Evolution**: Documentation is a living asset. As requirements evolve and refactoring occurs, the associated documentation must be updated in tandem.
- **Integral Component**: Documentation is not a post-implementation chore; it is treated as part of the implementation itself. An undocumented feature is an incomplete feature.

---

# AI Implementation Workflow

ATLAS utilizes a structured workflow to direct AI implementation agents through strict guardrails:

```
Design
  ↓
Review
  ↓
Approved Blueprint
  ↓
Implementation Prompt
  ↓
AI Implementation Agent
  ↓
Human Review
  ↓
Merge
```

1. **Design**: Establish architectural specs, file contracts, and schemas in the Blueprint directory.
2. **Review**: Humans and planning processes analyze the design for compliance with the constitution.
3. **Approved Blueprint**: The design is locked as the system-level source of truth.
4. **Implementation Prompt**: A context-dense instructions file is generated pointing to the specific Blueprint contracts.
5. **AI Implementation Agent**: The agent executes the changes within the bounded scope defined by the prompt.
6. **Human Review**: A human engineer reviews the diffs, tests, and documentation.
7. **Merge**: Once validated and approved, the code is integrated into the codebase.

---

# Review Checklist

Before any code is accepted or merged, it must be audited against the following checklist:

- **Correctness**: Does the code satisfy the functional requirements and handle edge cases and failures gracefully?
- **Readability**: Can a developer unfamiliar with this module understand its intent and flow quickly?
- **Maintainability**: Is the code easy to modify, extend, or refactor without introducing regression?
- **Modularity**: Are system boundaries respected, and are concerns cleanly separated?
- **Consistency**: Does the implementation adhere to the structural patterns and styling found in the existing codebase?
- **Documentation**: Are docstrings, comments, and schemas updated to reflect the changes?
- **Testability**: Are there appropriate unit, integration, or contract tests validating the correctness of the code?

---

# Definition of Done

A feature or change request is complete only when the following conditions are met:

1. **Implementation Satisfies Requirements**: The functional and non-functional specifications are completely implemented.
2. **Architecture Remains Consistent**: No shortcuts have been taken that bypass architectural boundaries, interface patterns, or structural rules.
3. **Documentation is Updated**: Associated blueprint documents, user documentation, and public-facing docstrings have been updated.
4. **Code is Understandable**: The code is clean, typed, well-commented, and avoids unnecessary complexity.
5. **Quality Review Passes**: Automated tests pass, static analysis checks run cleanly, and human code review has been completed and approved.

Completing functional implementation alone does not constitute completion.

---

# Closing Statement

> ATLAS is engineered as a long-term platform rather than a collection of features. Every contribution should strengthen the architecture, improve maintainability, and preserve the engineering principles defined in this document.
