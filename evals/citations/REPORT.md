# Citation-fabrication and pipeline eval

Model `claude-opus-5-5` via Claude Code print mode (all tools disabled; API-equivalent cost $30.86), Apple M4, 16 GB RAM. 20 project ideas from `ideas.yaml`. Run started 2026-11-18T04:52 UTC.

## Do the cited papers exist?

Each citation was checked against Crossref, arXiv, OpenAlex and Semantic Scholar: **verified** means a near-identical title was found with a matching author or year; **misattributed** means the title exists but the authors and year do not match; **not found** means every source was searched and none had a similar title; **unchecked** means a source could not be searched (rate limits), so no verdict is given. Percentages include unchecked citations; they are final only when that column is zero.

|  | Citations | Verified | Misattributed | Not found | Unchecked |
| --- | --- | --- | --- | --- | --- |
| Model asked directly | 100 | 99 (99.0%) | 0 (0.0%) | 1 (1.0%) | 0 |
|   ...research ideas | 50 | 49 (98.0%) | 0 (0.0%) | 1 (2.0%) | 0 |
|   ...engineering ideas | 50 | 50 (100.0%) | 0 (0.0%) | 0 (0.0%) | 0 |
| ATLAS research stage | 95 | 94 (98.9%) | 0 (0.0%) | 0 (0.0%) | 1 |
|   ...research ideas | 50 | 50 (100.0%) | 0 (0.0%) | 0 (0.0%) | 0 |
|   ...engineering ideas | 45 | 44 (97.8%) | 0 (0.0%) | 0 (0.0%) | 1 |

ATLAS cites only papers it retrieved, so any ATLAS citation not verified here is a miss by the checker itself, which estimates its false-negative rate. Ideas where ATLAS found no papers at all: 1.

Topical similarity of verified papers to the idea (cosine, local embedding model; higher is more on-topic): plain 0.671, ATLAS 0.637.

## The full pipeline

Projects taken through all four stages: **95.0%**. Each stage gets up to three attempts.

| Stage | Reached | First try | Eventually | Latency p50 / p95 (s) | Prompt tokens mean / max | Output tokens mean |
| --- | --- | --- | --- | --- | --- | --- |
| research | 20 | 75.0% | 95.0% | 34.04 / 53.49 | 5973 / 18601 | 3136 |
| planning | 19 | 100.0% | 100.0% | 60.82 / 71.02 | 10858 / 12149 | 6431 |
| architecture | 19 | 100.0% | 100.0% | 119.32 / 142.59 | 32571 / 37870 | 13022 |
| review | 19 | 100.0% | 100.0% | 66.72 / 121.05 | 56480 / 106915 | 6935 |

Latency and tokens cover every model call in a stage, including the evidence-summary call in research.

- Per completed project (median): 330.0 s, 5 model calls, 143557 tokens, 52 knowledge candidates.
- Largest prompt sent: 106915 tokens. Failed model calls: 0.
- Plain prompting, for comparison: 20.47 s and about 3737 tokens per request.

## Limits

- One model (claude-opus-5-5). Other models, small local ones especially, may invent more citations and pass fewer stages.
- The ideas and the checker were written by the eval's author. The checker matches titles, so a real paper cited under a garbled title counts as not found.
- Topical similarity is an embedding proxy, not a human judgement of relevance.
- Stage success means the draft passed ATLAS's schema and grounding checks and committed; it says nothing about whether the plan is good.

## Before and after a fix

The same eval run before the change and after it, on the 15 ideas that completed in both runs without a provider outage (usage limits, the machine sleeping).

| Stage | First try before | First try after | Eventually before | Eventually after |
| --- | --- | --- | --- | --- |
| research | 86.7% | 66.7% | 100.0% | 93.3% |
| planning | 100.0% | 100.0% | 100.0% | 100.0% |
| architecture | 33.3% | 100.0% | 53.3% | 100.0% |
| review | 100.0% | 100.0% | 100.0% | 100.0% |

Projects through all four stages: 53.3% before, 93.3% after.

## Research stage after the schema fix

Research only, rerun on all ideas after the draft schema told the model that every finding and opportunity must cite at least one retrieved item.

- Passed first try: 100.0% (20 ideas); within three tries: 100.0%.
- ATLAS citations: 100, verified 100 (100.0%), not found 0, misattributed 0, unchecked 0.
- API-equivalent cost: $4.7399.
