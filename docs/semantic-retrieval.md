# Semantic Knowledge Retrieval (optional)

By default, each stage is grounded in the newest published knowledge entries.
Set `ATLAS_EMBEDDING_ENABLED=true` to rank those entries by semantic similarity
to the project's objective and your instructions instead, using an embedded
[sqlite-vec](https://github.com/asg017/sqlite-vec) index at
`.atlas/knowledge.vec.db`. The index is a rebuildable cache: published
knowledge in `.atlas/knowledge.json` stays the source of truth, and entries are
embedded lazily on first retrieval. If embedding fails, retrieval falls back to
newest-first.

```bash
ATLAS_EMBEDDING_ENABLED=true
ATLAS_EMBEDDING_MODEL="nomic-embed-text"   # model name for your embedding backend
# Optional; protocol, endpoint and API key default to the ATLAS_AI_* values.
# ATLAS_EMBEDDING_PROTOCOL=OLLAMA
# ATLAS_EMBEDDING_ENDPOINT=http://localhost:11434
# ATLAS_EMBEDDING_API_KEY=...
```

Embeddings are supported for the `GEMINI`, `OLLAMA` and `OPENAI_COMPATIBLE`
protocols; `ANTHROPIC` has no embeddings API. Search is an exact cosine scan
(no ANN index), one vector per entry. See
[ADR-006](decisions/adr-006-semantic-knowledge-retrieval.md).

A labelled retrieval eval lives in `evals/retrieval/`:

```bash
uv run python -m evals.retrieval --model nomic-embed-text   # needs a running Ollama
```

On its 30 queries over 190 sections of this repo's own docs (a proxy corpus,
not reviewed knowledge; queries written by the feature's author), `nomic-embed-text`
gave hit@5 0.90 and MRR@20 0.79, against 0.83 and 0.64 for a BM25 keyword
baseline and 0.10 and 0.06 for the previous newest-first behaviour. The
advantage over BM25 is small and mostly within bootstrap noise at this sample
size. Full numbers are in `evals/retrieval/results.json`.
