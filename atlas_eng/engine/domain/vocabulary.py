"""Canonical Engineering Vocabulary for ATLAS.

This module defines the single source of truth for engineering terminology.
The terms defined here represent the ubiquitous language used throughout ATLAS.
They are documented conceptually rather than strictly enforced via Enums,
as the domain models themselves enforce behavioral semantics.

### Foundational Terms
- **Evidence**: Raw data, observations, or facts gathered during research.
- **Finding**: A synthesized conclusion drawn from one or more pieces of evidence.
- **Opportunity**: A potential improvement or feature identified from findings.
- **Constraint**: A strict limitation or boundary on system design or implementation.
- **Assumption**: A premise accepted as true without definitive proof to enable
  progress.

### Engineering & Lifecycle Terms
- **Engineering Decision**: A recorded, immutable architectural choice (e.g. ADR).
- **Snapshot**: An immutable capture of a subsystem's state at a specific
  workflow stage.
- **Acceptance Criteria**: Verifiable functional statements determining task
  completion.
- **Definition of Done**: Engineering quality standard metrics (tests, linting,
  docs) required for completion.
"""

# The vocabulary is purely conceptual documentation.
# Structural implementation resides in the specific domain models.
