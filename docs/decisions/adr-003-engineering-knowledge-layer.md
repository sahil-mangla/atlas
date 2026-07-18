# ADR-003: Engineering Knowledge Layer

## Status

Accepted — Phase 13.

## Decision

Engineering knowledge is isolated under `engine/knowledge/`. Workflow owns retrieval and post-commit extraction. Human review is required before publication. Published content is immutable. AI has no dependency on knowledge; knowledge enters generation only through immutable `ContextPayload`.

Knowledge persists in `.atlas/knowledge.json` through `KnowledgeRepository` and `FilesystemKnowledgeRepository`. Phase 13 intentionally uses direct Pydantic JSON serialization in the filesystem repository and does not add a knowledge-specific serializer layer.
