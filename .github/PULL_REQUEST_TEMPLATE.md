## Summary

<!-- What does this PR change, and why? -->

## Test plan

<!-- How was this verified? -->
- [ ] `uv run pytest`
- [ ] `uv run mypy .`
- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run python -m evals --ai-protocol SCRIPTED --ai-model scripted --baseline-path evals/baselines/scripted.json --no-latency-check`

## Checklist

- [ ] No new architectural subsystems/layers introduced without a corresponding ADR
- [ ] Public `atlas_eng` SDK contract unchanged, or the change is additive per `PLATFORM_API_VERSION` rules
- [ ] Documentation updated where applicable (`docs/`, `README.md`, `CHANGELOG.md`)
