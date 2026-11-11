# ADR-006: Semantic Knowledge Retrieval via an Embedded Vector Index

## Status

Accepted. Extends ADR-003 (Engineering Knowledge Layer).

## Context

`KnowledgeRetrievalService.retrieve` selected published knowledge by stage-profile
category and tag, then took the newest `max_entries`. Once a project has more
eligible entries than the cap, relevance played no part: a recent but unrelated
entry displaced an older, directly relevant one.

## Decision

Add optional semantic ranking behind the existing `retrieve()` call.

- **`.atlas/knowledge.json` remains the source of truth.** Eligibility (ACTIVE
  status, categories, tags) is still decided deterministically from the
  repository. Ranking only orders and caps entries that already passed it, so
  human review, immutability, and deprecation semantics are unchanged.
- **The vector index is a derived cache** at `.atlas/knowledge.vec.db`
  (`SqliteVecStore`, sqlite-vec, exact cosine scan). It can be deleted at any
  time. Entries are embedded lazily and keyed by `deduplication_fingerprint`
  (immutable content), so there are no hooks on publish/supersede/deprecate and
  existing projects index themselves on first use. A different embedding model
  gets its own vectors via `model_id`.
- **Query text** = caller instructions, then project objective and description.
  `generate_proposal` now passes `user_instructions` through
  `retrieve_for_stage`.
- **Never worse than before.** Any ranker, store, or embedder failure logs a
  warning and falls back to newest-first. The feature is off by default
  (`ATLAS_EMBEDDING_ENABLED=false`); misconfiguration disables it rather than
  stopping startup.
- **Boundary kept.** `Embedder` and `VectorStore` are defined in
  `engine/knowledge` (the subsystem may not import `engine.ai`). Concrete
  `EmbeddingProvider` adapters live in `engine/ai`, are separate from
  `AIProvider` (Anthropic has no embeddings API), and are wired in
  `atlas/_bootstrap.py`.

## Configuration

| Variable | Default | Notes |
| --- | --- | --- |
| `ATLAS_EMBEDDING_ENABLED` | `false` | Opt in. |
| `ATLAS_EMBEDDING_PROTOCOL` | `ATLAS_AI_PROTOCOL` | `GEMINI`, `OPENAI_COMPATIBLE`, `OLLAMA`. |
| `ATLAS_EMBEDDING_ENDPOINT` | `ATLAS_AI_ENDPOINT` | |
| `ATLAS_EMBEDDING_MODEL` | none | Required for Ollama / OpenAI-compatible; Gemini defaults to `gemini-embedding-001`. Not the chat model. |
| `ATLAS_EMBEDDING_API_KEY` | `ATLAS_AI_API_KEY` | Gemini also reads `ATLAS_GEMINI_API_KEY`. |

## Consequences

- Cost: one query embedding per proposal generation, plus a one-time embedding
  of each new entry. Retrieval is skipped for a single eligible entry.
- Exact scan is appropriate for per-project corpora (hundreds of entries). If a
  corpus grows into the tens of thousands, swap in a `vec0`/ANN-backed
  `VectorStore` without touching callers.
- Not done: asymmetric document/query embedding task types, and applying the
  same index to research retrieval or memory.
