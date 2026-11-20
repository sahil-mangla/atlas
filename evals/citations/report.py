"""Render ``results.json`` from the citation eval as a Markdown report.

Usage::

    uv run python -m evals.citations.report [results.json [before.json]] > REPORT.md
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


def _row(cells: list[Any]) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


def _provider(data: dict[str, Any]) -> str:
    if data.get("provider") == "claude-code":
        cost = data.get("api_equivalent_cost_usd")
        extra = f"; API-equivalent cost ${cost:.2f}" if cost is not None else ""
        return f"Claude Code print mode (all tools disabled{extra})"
    return f"Ollama {' '.join(data.get('ollama_version', []))}".strip()


def render(
    data: dict[str, Any],
    before: dict[str, Any] | None = None,
    research_fix: dict[str, Any] | None = None,
) -> str:
    s = data["summary"]
    m = data.get("machine", {})
    memory = m.get("memory_bytes", "")
    memory_gb = f"{int(memory) / 2**30:.0f} GB" if memory.isdigit() else "unknown"
    lines = [
        "# Citation-fabrication and pipeline eval",
        "",
        f"Model `{data['model']}` via {_provider(data)}, "
        f"{m.get('chip', 'unknown chip')}, {memory_gb} RAM. "
        f"{s['ideas']} project ideas from `ideas.yaml`. "
        f"Run started {data['started'][:16]} UTC.",
        "",
        "## Do the cited papers exist?",
        "",
        "Each citation was checked against Crossref, arXiv, OpenAlex and Semantic "
        "Scholar: "
        "**verified** means a near-identical title was found with a matching author "
        "or year; **misattributed** means the title exists but the authors and year "
        "do not match; **not found** means every source was searched and none had "
        "a similar title; **unchecked** means a source could not be searched (rate "
        "limits), so no verdict is given. Percentages include unchecked citations; "
        "they are final only when that column is zero.",
        "",
        _row(["", "Citations", "Verified", "Misattributed", "Not found", "Unchecked"]),
        _row(["---"] * 6),
    ]
    for arm, label in (
        ("plain", "Model asked directly"),
        ("atlas", "ATLAS research stage"),
    ):
        for kind in ("all", "research", "engineering"):
            c = s[f"{arm}_{kind}"]
            name = label if kind == "all" else f"  ...{kind} ideas"
            lines.append(
                _row(
                    [
                        name,
                        c["total"],
                        f"{c['verified']} ({c['verified_pct']}%)",
                        f"{c['misattributed']} ({c['misattributed_pct']}%)",
                        f"{c['not_found']} ({c['not_found_pct']}%)",
                        c["unchecked"],
                    ]
                )
            )
    lines += [
        "",
        f"ATLAS cites only papers it retrieved, so any ATLAS citation not verified "
        f"here is a miss by the checker itself, which estimates its false-negative "
        f"rate. Ideas where ATLAS found no papers at all: "
        f"{s['atlas_ideas_with_no_evidence']}.",
        "",
        "Topical similarity of verified papers to the idea (cosine, local "
        f"embedding model; higher is more on-topic): plain "
        f"{s['plain_all']['median_relevance_of_verified']}, ATLAS "
        f"{s['atlas_all']['median_relevance_of_verified']}.",
        "",
        "## The full pipeline",
        "",
        f"Projects taken through all four stages: **{s['projects_completed_pct']}%**. "
        f"Each stage gets up to three attempts.",
        "",
        _row(
            [
                "Stage",
                "Reached",
                "First try",
                "Eventually",
                "Latency p50 / p95 (s)",
                "Prompt tokens mean / max",
                "Output tokens mean",
            ]
        ),
        _row(["---"] * 7),
    ]
    for stage, st in s["stages"].items():
        lines.append(
            _row(
                [
                    stage,
                    st["reached"],
                    f"{st['first_try_pct']}%",
                    f"{st['eventual_pct']}%",
                    f"{st['latency_s_p50']} / {st['latency_s_p95']}",
                    f"{st['prompt_tokens_mean']} / {st['prompt_tokens_max']}",
                    st["completion_tokens_mean"],
                ]
            )
        )
    p = s["per_project"]
    pp = s["plain_prompt"]
    lines += [
        "",
        "Latency and tokens cover every model call in a stage, including the "
        "evidence-summary call in research.",
        "",
        f"- Per completed project (median): {p['wall_s_median']} s, "
        f"{p['model_calls_median']:.0f} model calls, {p['tokens_median']:.0f} tokens, "
        f"{p['knowledge_candidates_median']:.0f} knowledge candidates.",
        f"- Largest prompt sent: {s['max_prompt_tokens_seen']} tokens. Failed model "
        f"calls: {s['failed_calls']}.",
        f"- Plain prompting, for comparison: {pp['latency_s_p50']} s and about "
        f"{pp['prompt_tokens_mean'] + pp['completion_tokens_mean']} tokens "
        "per request.",
        "",
        "## Limits",
        "",
        f"- One model ({data['model']}). Other models, small local ones "
        "especially, may invent more citations and pass fewer stages.",
        "- The ideas and the checker were written by the eval's author. The checker "
        "matches titles, so a real paper cited under a garbled title counts as "
        "not found.",
        "- Topical similarity is an embedding proxy, not a human judgement of "
        "relevance.",
        "- Stage success means the draft passed ATLAS's schema and grounding checks "
        "and committed; it says nothing about whether the plan is good.",
    ]
    excluded = data.get("excluded_for_session_limit") or []
    if excluded:
        lines.append(
            f"- Left out because the Claude subscription's usage limit cut them "
            f"off, not because ATLAS failed: {', '.join(excluded)}."
        )
    if before is not None:
        lines += _comparison(before, data)
    if research_fix is not None:
        lines += _research_fix(research_fix)
    return "\n".join(lines) + "\n"


def _comparable(ideas: list[dict[str, Any]], names: set[str]) -> dict[str, Any]:
    """Summary of the ideas in ``names`` that no provider outage touched."""
    from evals.citations.run import _load_idea, summarise  # noqa: PLC0415

    return summarise(
        [
            _load_idea(idea)
            for idea in ideas
            if idea["name"] in names and "AIProviderError" not in json.dumps(idea)
        ]
    )


def _comparison(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    clean = {
        idea["name"]
        for idea in before["ideas"]
        if "AIProviderError" not in json.dumps(idea)
    } & {
        idea["name"]
        for idea in after["ideas"]
        if "AIProviderError" not in json.dumps(idea)
    }
    b = _comparable(before["ideas"], clean)
    a = _comparable(after["ideas"], clean)
    lines = [
        "",
        "## Before and after a fix",
        "",
        f"The same eval run before the change and after it, on the {b['ideas']} "
        "ideas that completed in both runs without a provider outage (usage "
        "limits, the machine sleeping).",
        "",
        _row(
            [
                "Stage",
                "First try before",
                "First try after",
                "Eventually before",
                "Eventually after",
            ]
        ),
        _row(["---"] * 5),
    ]
    for stage, st in a["stages"].items():
        old = b["stages"].get(stage, {})
        lines.append(
            _row(
                [
                    stage,
                    f"{old.get('first_try_pct', '-')}%",
                    f"{st['first_try_pct']}%",
                    f"{old.get('eventual_pct', '-')}%",
                    f"{st['eventual_pct']}%",
                ]
            )
        )
    lines += [
        "",
        f"Projects through all four stages: {b['projects_completed_pct']}% before, "
        f"{a['projects_completed_pct']}% after.",
    ]
    return lines


def _research_fix(data: dict[str, Any]) -> list[str]:
    s = data["summary"]
    st = s["stages"]["research"]
    c = s["atlas_all"]
    return [
        "",
        "## Research stage after the schema fix",
        "",
        "Research only, rerun on all ideas after the draft schema told the model "
        "that every finding and opportunity must cite at least one retrieved "
        "item.",
        "",
        f"- Passed first try: {st['first_try_pct']}% ({st['reached']} ideas); "
        f"within three tries: {st['eventual_pct']}%.",
        f"- ATLAS citations: {c['total']}, verified {c['verified']} "
        f"({c['verified_pct']}%), not found {c['not_found']}, misattributed "
        f"{c['misattributed']}, unchecked {c['unchecked']}.",
        f"- API-equivalent cost: ${data.get('api_equivalent_cost_usd')}.",
    ]


def _read_optional(args: list[str], index: int) -> dict[str, Any] | None:
    if index >= len(args):
        return None
    return json.loads(Path(args[index]).read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def main() -> int:
    args = sys.argv[1:]
    path = Path(args[0]) if args else HERE / "results.json"
    before = _read_optional(args, 1)
    fixed = _read_optional(args, 2)
    data = json.loads(path.read_text(encoding="utf-8"))
    sys.stdout.write(render(data, before, fixed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
