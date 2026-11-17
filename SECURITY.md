# Security Policy

## Reporting a vulnerability

Please report security problems privately, not in a public issue. Use
GitHub's private reporting: on the repository's **Security** tab, choose
**Report a vulnerability**. Include what an attacker could do, the steps to
reproduce it, and the ATLAS version (`atlas --version`).

You should hear back within a week. Once a fix is released, the advisory is
published with credit to you unless you prefer otherwise.

## Supported versions

Only the latest release receives security fixes.

## What ATLAS stores, and where

ATLAS runs locally and has no server of its own. Things to know when deploying
it:

- **API keys** are read from the environment or a `.env` file. `atlas init`
  writes `.env` readable only by you (where the filesystem supports it) and
  warns if git would commit it. Never commit `.env`.
- **Prompts and model output** are sent to the AI provider you configure, and
  nowhere else unless you enable Langfuse.
- **Trace files** under `<workspace>/traces/` and the Langfuse integration may
  contain prompt and proposal text. Treat them like the project data itself.
- **Research retrieval** sends keywords from the project's objective and
  description to arXiv, Semantic Scholar and OpenAlex. The `SCRIPTED`
  protocol makes no network requests at all.
