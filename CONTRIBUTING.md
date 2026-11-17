# Contributing to ATLAS

Thanks for helping. This page covers what you need to make a change and get
it merged. No API key or AI model is needed for any of it.

## Set up

You need Python 3.12 or newer and [uv](https://github.com/astral-sh/uv).

```bash
git clone https://github.com/sahil-mangla/atlas.git
cd atlas
uv sync                      # installs ATLAS, both optional extras and dev tools
uv run atlas demo            # the whole workflow, offline
```

## Check your change

Run these before opening a pull request; CI runs the same on Linux, macOS
and Windows with Python 3.12 and 3.13.

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest
uv run python -m evals --ai-protocol SCRIPTED --ai-model scripted \
  --baseline-path evals/baselines/scripted.json --no-latency-check
```

To run the formatting, lint and type checks on every commit:

```bash
uv run pre-commit install
```

Tests run with outbound network access blocked. Anything that needs a model
uses the offline `SCRIPTED` protocol; see
[Testing Without an AI Provider](docs/testing.md) for the test layers and how
to write tests against a real platform with `atlas_eng.testing`.

## Where code goes

Everything lives under the `atlas_eng` package, in layers with one-way
dependencies, which tests in `tests/architecture/` enforce:

| Layer | Path | May import |
|---|---|---|
| Clients (CLI) | `atlas_eng/clients/` | the SDK, never the engine |
| SDK | `atlas_eng/` (top level) | engine, presentation, shared |
| Presentation | `atlas_eng/presentation/` | the SDK's public types, never the engine |
| Engine | `atlas_eng/engine/` | `shared` only |
| Shared | `atlas_eng/shared/` | nothing above it |

[System Overview](docs/architecture/system-overview.md) and the
[Extension Guide](docs/architecture/extension-guide.md) explain the design,
including how to add an AI protocol or a workflow stage.

## Pull requests

- Keep each pull request to one change, and say why it is needed.
- Add or update tests for behaviour you change. A bug fix should come with a
  test that fails without it.
- Changes to the public SDK (`atlas_eng` commands, results and exceptions)
  must be additive within a major version; see
  `atlas_eng/contracts/version.py`.
- Update `CHANGELOG.md` under `[Unreleased]`, and the docs where behaviour
  changes.
- A new layer or subsystem needs an ADR in `docs/decisions/`.

## Reporting bugs and security issues

Use the issue templates for bugs and feature requests. Do not open a public
issue for a security problem; see [SECURITY.md](SECURITY.md).
