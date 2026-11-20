"""Citation-fabrication and pipeline eval against a local Ollama model.

For each project idea in ``ideas.yaml`` this runs, on the same model:

* **Plain prompting** -- one request asking the model directly for relevant
  papers, with the instruction to include only papers it is sure exist.
* **ATLAS** -- the real platform, taking the idea through research,
  planning, architecture and review, approving each stage.

Every citation from both arms is checked against OpenAlex, arXiv and
Semantic Scholar (``verify.py``). Every model call ATLAS makes is recorded:
stage, prompt and completion tokens, latency and failures.

Usage::

    uv run python -m evals.citations.run --model qwen2.5-coder:7b

Run it from a directory with no ``.env`` above it (the runner changes into a
temporary directory itself), so local settings such as Langfuse keys never
apply. Results go to ``evals/citations/results.json``.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import re
import statistics
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import yaml

HERE = Path(__file__).resolve().parent


def _say(*parts: object) -> None:
    sys.stdout.write(" ".join(str(p) for p in parts) + "\n")
    sys.stdout.flush()


STAGES = ("research", "planning", "architecture", "review")
MAX_ATTEMPTS = 3
PAPERS_REQUESTED = 5

BASELINE_SYSTEM = "You are a careful research assistant for software engineers."
BASELINE_TASK = (
    "Project: {name}\n{description}\nObjective: {objective}\n\n"
    "List {n} published academic papers (peer-reviewed or arXiv) that are the "
    "most relevant evidence for this project. For each, give the exact title, "
    "the authors, the year and the venue. Only include papers you are confident "
    "really exist."
)
BASELINE_SCHEMA = {
    "type": "object",
    "properties": {
        "papers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "authors": {"type": "array", "items": {"type": "string"}},
                    "year": {"type": "integer"},
                    "venue": {"type": "string"},
                },
                "required": ["title", "authors", "year"],
            },
        }
    },
    "required": ["papers"],
}


@dataclass
class Call:
    """One model request made by ATLAS."""

    stage: str
    schema: str
    attempt: int
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_s: float = 0.0
    prompt_chars: int = 0
    error: str = ""


@dataclass
class StageResult:
    stage: str
    attempts: int = 0
    succeeded: bool = False
    errors: list[str] = field(default_factory=list)
    headline: str = ""


@dataclass
class Citation:
    title: str
    authors: list[str]
    year: int | None
    status: str = ""
    title_similarity: float = 0.0
    matched_title: str = ""
    relevance: float | None = None


@dataclass
class IdeaResult:
    name: str
    kind: str
    baseline_citations: list[Citation] = field(default_factory=list)
    baseline_tokens: dict[str, int] = field(default_factory=dict)
    baseline_latency_s: float = 0.0
    baseline_error: str = ""
    atlas_citations: list[Citation] = field(default_factory=list)
    stages: list[StageResult] = field(default_factory=list)
    calls: list[Call] = field(default_factory=list)
    knowledge_candidates: int = 0
    atlas_wall_s: float = 0.0
    #: Evidence types, the items found and the findings drawn from them.
    research_notes: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Plain-prompting arm
# ---------------------------------------------------------------------------


def run_baseline(
    client: httpx.Client,
    endpoint: str,
    model: str,
    idea: dict[str, str],
    claude_code: Any = None,
) -> tuple[list[Citation], dict[str, int], float, str]:
    started = time.monotonic()
    if claude_code is not None:
        return _baseline_claude_code(claude_code, idea, started)
    try:
        response = client.post(
            f"{endpoint}/api/generate",
            json={
                "model": model,
                "system": BASELINE_SYSTEM,
                "prompt": BASELINE_TASK.format(n=PAPERS_REQUESTED, **idea),
                "format": BASELINE_SCHEMA,
                "stream": False,
            },
        )
        response.raise_for_status()
        data = response.json()
        papers = json.loads(data["response"]).get("papers", [])
    except (httpx.HTTPError, json.JSONDecodeError, KeyError) as error:
        return [], {}, time.monotonic() - started, str(error)
    citations = [
        Citation(
            title=str(p.get("title", "")),
            authors=[str(a) for a in p.get("authors", []) if a],
            year=p.get("year") if isinstance(p.get("year"), int) else None,
        )
        for p in papers
        if isinstance(p, dict)
    ]
    tokens = {
        "prompt": int(data.get("prompt_eval_count", 0)),
        "completion": int(data.get("eval_count", 0)),
    }
    return citations, tokens, time.monotonic() - started, ""


def _baseline_claude_code(
    provider: Any, idea: dict[str, str], started: float
) -> tuple[list[Citation], dict[str, int], float, str]:
    from atlas_eng.engine.ai.exceptions import AIProviderException  # noqa: PLC0415

    try:
        content, reply = provider.run(
            BASELINE_SYSTEM,
            BASELINE_TASK.format(n=PAPERS_REQUESTED, **idea),
            BASELINE_SCHEMA,
        )
        papers = json.loads(content).get("papers", [])
    except (AIProviderException, json.JSONDecodeError) as error:
        return [], {}, time.monotonic() - started, str(error)[:300]
    usage = reply.get("usage") or {}
    citations = [
        Citation(
            title=str(p.get("title", "")),
            authors=[str(a) for a in p.get("authors", []) if a],
            year=p.get("year") if isinstance(p.get("year"), int) else None,
        )
        for p in papers
        if isinstance(p, dict)
    ]
    tokens = {
        "prompt": int(usage.get("input_tokens", 0))
        + int(usage.get("cache_creation_input_tokens", 0))
        + int(usage.get("cache_read_input_tokens", 0)),
        "completion": int(usage.get("output_tokens", 0)),
    }
    return citations, tokens, time.monotonic() - started, ""


# ---------------------------------------------------------------------------
# ATLAS arm
# ---------------------------------------------------------------------------


class _Recorder:
    """Wraps the real provider and records every call the platform makes."""

    def __init__(self, inner: Any, dump_dir: Path | None = None) -> None:
        self._inner = inner
        self._dump_dir = dump_dir
        self.calls: list[Call] = []
        self.stage = ""
        self.attempt = 0

    def generate(self, request: Any) -> Any:
        schema = str((request.response_schema or {}).get("title", ""))
        call = Call(
            stage=self.stage,
            schema=schema,
            attempt=self.attempt,
            prompt_chars=len(request.prompt.system_prompt)
            + len(request.prompt.user_prompt),
        )
        started = time.monotonic()
        try:
            response = self._inner.generate(request)
        except Exception as error:
            call.error = str(error)[:300]
            raise
        finally:
            call.latency_s = round(time.monotonic() - started, 2)
            self.calls.append(call)
        call.prompt_tokens = response.usage_metrics.get("prompt_tokens", 0)
        call.completion_tokens = response.usage_metrics.get("completion_tokens", 0)
        if self._dump_dir is not None:
            name = f"{len(self.calls):02d}-{self.stage}-a{self.attempt}-{schema}.json"
            (self._dump_dir / name).write_text(response.content, encoding="utf-8")
        return response

    def capabilities(self) -> Any:
        return self._inner.capabilities()


def _research_notes(content: dict[str, Any]) -> dict[str, Any]:
    evidence = content.get("evidence", [])
    types: dict[str, int] = {}
    for item in evidence:
        types[item.get("type", "paper")] = types.get(item.get("type", "paper"), 0) + 1
    return {
        "evidence_types": types,
        "market_items": [
            {
                "type": item.get("type"),
                "title": item.get("title"),
                "origin": item.get("origin"),
                "summary": item.get("summary"),
            }
            for item in evidence
            if item.get("type", "paper") != "paper"
        ],
        "findings": [
            {"title": f.get("title"), "summary": f.get("summary")}
            for f in content.get("findings", [])
        ],
        "opportunities": [
            {"title": o.get("title"), "description": o.get("description")}
            for o in content.get("opportunities", [])
        ],
    }


def _parse_citation(evidence: dict[str, Any]) -> Citation:
    citation = str(evidence.get("citation", ""))
    authors_part = citation.split(" (", 1)[0] if " (" in citation else ""
    authors = [
        a.strip()
        for a in authors_part.replace(" et al.", "").split(",")
        if a.strip() and a.strip() != "Unknown Author"
    ]
    year_match = re.search(r"\((\d{4})\)", citation)
    return Citation(
        title=str(evidence.get("title", "")),
        authors=authors,
        year=int(year_match.group(1)) if year_match else None,
    )


def run_atlas(
    idea: dict[str, str],
    workspace: Path,
    recorder_box: list[_Recorder],
    stages: tuple[str, ...] = STAGES,
) -> IdeaResult:
    from atlas_eng import create  # noqa: PLC0415 - after the environment is set
    from atlas_eng.commands import (  # noqa: PLC0415
        ApproveProposalCommand,
        CreateProjectCommand,
        ExecuteStageCommand,
        ListKnowledgeCandidatesCommand,
        TransitionStageCommand,
    )
    from atlas_eng.exceptions import ApplicationError  # noqa: PLC0415
    from atlas_eng.types import WorkflowStage  # noqa: PLC0415

    os.environ["ATLAS_WORKSPACE_ROOT"] = str(workspace)
    platform_ = create()
    recorder = recorder_box[-1]
    result = IdeaResult(name=idea["name"], kind=idea["kind"])
    started = time.monotonic()
    project = platform_.create_project(
        CreateProjectCommand(
            name=idea["name"],
            description=idea["description"],
            objective=idea["objective"],
        )
    )
    platform_.transition_stage(
        TransitionStageCommand(project_id=project.id, reason="eval")
    )
    headline_field = {
        "research": "problem_statement",
        "planning": "scope_statement",
        "architecture": "design_summary",
        "review": "synthesis",
    }
    for stage in stages:
        outcome = StageResult(stage=stage)
        recorder.stage = stage
        while outcome.attempts < MAX_ATTEMPTS and not outcome.succeeded:
            outcome.attempts += 1
            recorder.attempt = outcome.attempts
            try:
                proposal = platform_.execute_stage(
                    ExecuteStageCommand(
                        project_id=project.id, stage=WorkflowStage(stage)
                    )
                )
                if stage == "research":
                    result.research_notes = _research_notes(proposal.content)
                    result.atlas_citations = [
                        _parse_citation(e)
                        for e in proposal.content.get("evidence", [])
                        if e.get("type", "paper") == "paper"
                    ]
                committed = platform_.approve_proposal(
                    ApproveProposalCommand(
                        project_id=project.id, proposal_id=proposal.id
                    )
                )
                if not committed.success:
                    outcome.errors.append(committed.patch_summary[:300])
                    continue
                outcome.succeeded = True
                outcome.headline = str(proposal.content.get(headline_field[stage], ""))[
                    :200
                ]
            except ApplicationError as error:
                outcome.errors.append(f"{type(error).__name__}: {str(error)[:300]}")
        result.stages.append(outcome)
        if not outcome.succeeded:
            break
    result.knowledge_candidates = len(
        platform_.list_knowledge_candidates(
            ListKnowledgeCandidatesCommand(project_id=project.id)
        ).candidates
    )
    result.atlas_wall_s = round(time.monotonic() - started, 1)
    result.calls = list(recorder.calls)
    recorder.calls.clear()
    return result


# ---------------------------------------------------------------------------
# Relevance (topical similarity) via the local embedding model
# ---------------------------------------------------------------------------


def _embed(
    client: httpx.Client, endpoint: str, model: str, texts: list[str]
) -> list[list[float]]:
    response = client.post(
        f"{endpoint}/api/embed", json={"model": model, "input": texts}
    )
    response.raise_for_status()
    vectors: list[list[float]] = response.json()["embeddings"]
    return vectors


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _machine() -> dict[str, str]:
    info = {
        "python": platform.python_version(),
        "os": f"{platform.system()} {platform.release()}",
    }
    if sys.platform == "darwin":
        for key, name in (
            ("chip", "machdep.cpu.brand_string"),
            ("memory_bytes", "hw.memsize"),
        ):
            info[key] = subprocess.run(
                ["sysctl", "-n", name], capture_output=True, text=True, check=False
            ).stdout.strip()
    return info


def main(argv: list[str] | None = None) -> int:  # noqa: PLR0912, PLR0915
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--provider",
        choices=("ollama", "claude-code"),
        default="ollama",
        help="claude-code runs requests through your local Claude Code login.",
    )
    parser.add_argument("--model", default=None)
    parser.add_argument(
        "--resume", action="store_true", help="Skip ideas already in --out."
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Re-check citations marked unchecked in --out; generate nothing.",
    )
    parser.add_argument("--embed-model", default="nomic-embed-text")
    parser.add_argument("--endpoint", default="http://localhost:11434")
    parser.add_argument("--limit", type=int, default=0, help="Only the first N ideas.")
    parser.add_argument("--out", type=Path, default=HERE / "results.json")
    parser.add_argument(
        "--ideas",
        type=Path,
        default=HERE / "ideas.yaml",
        help="YAML file of ideas to run.",
    )
    parser.add_argument(
        "--market",
        action="store_true",
        help="Search for existing products too, not only papers.",
    )
    parser.add_argument(
        "--skip-baseline",
        action="store_true",
        help="Do not run the plain-prompting arm.",
    )
    parser.add_argument(
        "--only", action="append", default=[], help="Run only this idea (repeatable)."
    )
    parser.add_argument(
        "--dump-dir", type=Path, default=None, help="Save every raw model reply here."
    )
    parser.add_argument(
        "--stages",
        default=",".join(STAGES),
        help="Comma-separated stages to run, in order (default: all four).",
    )
    args = parser.parse_args(argv)
    args.stages = tuple(s.strip() for s in args.stages.split(",") if s.strip())
    # Resolved now: the run changes into a temporary directory later.
    args.out = args.out.resolve()
    if args.dump_dir is not None:
        args.dump_dir = args.dump_dir.resolve()
        args.dump_dir.mkdir(parents=True, exist_ok=True)
    if args.model is None:
        args.model = (
            "claude-opus-5-5" if args.provider == "claude-code" else "qwen2.5-coder:7b"
        )

    ideas = yaml.safe_load(args.ideas.read_text(encoding="utf-8"))["ideas"]
    if args.only:
        ideas = [idea for idea in ideas if idea["name"] in args.only]
    if args.limit:
        ideas = ideas[: args.limit]

    if args.verify_only:
        return _verify_only(args)

    sandbox = Path(tempfile.mkdtemp(prefix="atlas-citation-eval-"))
    os.chdir(sandbox)  # no .env above here, so local settings cannot apply
    os.environ.update(
        {
            "ATLAS_AI_PROTOCOL": "OLLAMA",
            "ATLAS_AI_MODEL": args.model,
            "ATLAS_AI_ENDPOINT": args.endpoint,
            "ATLAS_AI_TIMEOUT_SECONDS": "900",
            "ATLAS_INSTRUMENTATION_ENABLED": "false",
            "ATLAS_EMBEDDING_ENABLED": "false",
            # Paper-citation runs keep market research out of the numbers.
            "ATLAS_RESEARCH_MARKET_SOURCES": "true" if args.market else "false",
        }
    )
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"):
        os.environ.pop(name, None)

    from atlas_eng.engine.ai import factory  # noqa: PLC0415

    recorder_box: list[_Recorder] = []
    original_resolve = factory.ProtocolFactory.resolve

    claude_code = None
    if args.provider == "claude-code":
        from evals.citations.claude_code import ClaudeCodeProvider  # noqa: PLC0415

        claude_code = ClaudeCodeProvider(args.model)

    def recording_resolve(self: Any, config: Any, settings: Any = None) -> Any:
        inner = claude_code or original_resolve(self, config, settings)
        recorder = _Recorder(inner, args.dump_dir)
        recorder_box.append(recorder)
        return recorder

    factory.ProtocolFactory.resolve = recording_resolve  # type: ignore[method-assign]

    from evals.citations.verify import Verifier  # noqa: PLC0415

    verifier = Verifier(HERE / ".verify_cache.json")
    client = httpx.Client(timeout=900)
    results: list[IdeaResult] = []
    run_started = datetime.now(UTC)
    done: set[str] = set()
    if args.resume and args.out.exists():
        previous = json.loads(args.out.read_text(encoding="utf-8"))
        run_started = datetime.fromisoformat(previous["started"])
        results = [_load_idea(r) for r in previous["ideas"]]
        done = {r.name for r in results}
        _say(f"Resuming: {len(done)} ideas already done.")
    args.claude_code = claude_code
    try:
        for index, idea in enumerate(ideas, start=1):
            if idea["name"] in done:
                continue
            _say(f"[{index}/{len(ideas)}] {idea['name']}")
            citations, tokens, latency, error = (
                ([], {}, 0.0, "")
                if args.skip_baseline
                else run_baseline(client, args.endpoint, args.model, idea, claude_code)
            )
            result = run_atlas(idea, sandbox / f"ws-{index}", recorder_box, args.stages)
            result.baseline_citations, result.baseline_tokens = citations, tokens
            result.baseline_latency_s, result.baseline_error = round(latency, 2), error
            for citation in (*result.baseline_citations, *result.atlas_citations):
                verdict = verifier.verify(
                    citation.title, citation.authors, citation.year
                )
                citation.status = verdict.status
                citation.title_similarity = verdict.title_similarity
                citation.matched_title = verdict.matched_title
            all_citations = [*result.baseline_citations, *result.atlas_citations]
            if all_citations:
                vectors = _embed(
                    client,
                    args.endpoint,
                    args.embed_model,
                    [f"{idea['description']} {idea['objective']}"]
                    + [c.title or "(empty)" for c in all_citations],
                )
                for citation, vector in zip(all_citations, vectors[1:], strict=True):
                    citation.relevance = round(_cosine(vectors[0], vector), 3)
            stages = " ".join(
                f"{s.stage}:{'ok' if s.succeeded else 'FAIL'}x{s.attempts}"
                for s in result.stages
            )
            base_ok = sum(c.status == "verified" for c in result.baseline_citations)
            base_unchecked = sum(
                c.status == "unchecked" for c in result.baseline_citations
            )
            _say(
                f"    plain: {base_ok}/{len(result.baseline_citations)} verified"
                f" ({base_unchecked} unchecked;"
                f" skipping {sorted(verifier.unavailable)}) | "
                f"atlas: {len(result.atlas_citations)} citations | {stages} | "
                f"{result.atlas_wall_s}s"
            )
            results.append(result)
            _write(args, results, run_started)
    finally:
        verifier.close()
        client.close()
    _say(json.dumps(summarise(results), indent=2))
    return 0


def _write(
    args: argparse.Namespace, results: list[IdeaResult], started: datetime
) -> None:
    claude_code = getattr(args, "claude_code", None)
    payload = {
        "started": started.isoformat(),
        "provider": args.provider,
        "model": args.model,
        "api_equivalent_cost_usd": round(claude_code.cost_usd, 4)
        if claude_code
        else None,
        "claude_code_model_usage": claude_code.model_usage if claude_code else None,
        "embed_model": args.embed_model,
        "machine": _machine(),
        "ollama_version": subprocess.run(
            ["ollama", "--version"], capture_output=True, text=True, check=False
        )
        .stdout.strip()
        .splitlines()[0:1],
        "summary": summarise(results),
        "ideas": [asdict(r) for r in results],
    }
    args.out.write_text(json.dumps(payload, indent=1), encoding="utf-8")


def _verify_only(args: argparse.Namespace) -> int:
    """Re-check citations an earlier run could not check (rate limits, outages)."""
    from evals.citations.verify import Verifier  # noqa: PLC0415

    data = json.loads(args.out.read_text(encoding="utf-8"))
    results = [_load_idea(r) for r in data["ideas"]]
    verifier = Verifier(HERE / ".verify_cache.json")
    rechecked = 0
    try:
        for result in results:
            for citation in (*result.baseline_citations, *result.atlas_citations):
                if citation.status != "unchecked":
                    continue
                verdict = verifier.verify(
                    citation.title, citation.authors, citation.year
                )
                citation.status = verdict.status
                citation.title_similarity = verdict.title_similarity
                citation.matched_title = verdict.matched_title
                rechecked += 1
    finally:
        verifier.close()
    data["summary"] = summarise(results)
    data["ideas"] = [asdict(r) for r in results]
    args.out.write_text(json.dumps(data, indent=1), encoding="utf-8")
    left = sum(
        c.status == "unchecked"
        for r in results
        for c in (*r.baseline_citations, *r.atlas_citations)
    )
    _say(
        f"Re-checked {rechecked}; still unchecked: {left}; "
        f"unavailable sources: {sorted(verifier.unavailable) or 'none'}"
    )
    return 0


def _load_idea(raw: dict[str, Any]) -> IdeaResult:
    """Rebuild an ``IdeaResult`` saved by an earlier, interrupted run."""
    result = IdeaResult(name=raw["name"], kind=raw["kind"])
    result.baseline_citations = [Citation(**c) for c in raw["baseline_citations"]]
    result.atlas_citations = [Citation(**c) for c in raw["atlas_citations"]]
    result.stages = [StageResult(**st) for st in raw["stages"]]
    result.calls = [Call(**c) for c in raw["calls"]]
    for name in (
        "baseline_tokens",
        "baseline_latency_s",
        "baseline_error",
        "knowledge_candidates",
        "atlas_wall_s",
    ):
        setattr(result, name, raw[name])
    result.research_notes = raw.get("research_notes", {})
    return result


def _pct(part: int, whole: int) -> float:
    return round(100 * part / whole, 1) if whole else 0.0


def _p(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(q * len(ordered)))], 2)


def summarise(results: list[IdeaResult]) -> dict[str, Any]:
    def citation_stats(citations: list[Citation]) -> dict[str, Any]:
        counts = {
            s: sum(c.status == s for c in citations)
            for s in ("verified", "misattributed", "not_found", "unchecked")
        }
        relevance = [
            c.relevance
            for c in citations
            if c.relevance is not None and c.status == "verified"
        ]
        return {
            "total": len(citations),
            **counts,
            **{f"{s}_pct": _pct(n, len(citations)) for s, n in counts.items()},
            "median_relevance_of_verified": round(statistics.median(relevance), 3)
            if relevance
            else None,
        }

    out: dict[str, Any] = {"ideas": len(results)}
    for kind in ("all", "research", "engineering"):
        subset = [r for r in results if kind in ("all", r.kind)]
        out[f"plain_{kind}"] = citation_stats(
            [c for r in subset for c in r.baseline_citations]
        )
        out[f"atlas_{kind}"] = citation_stats(
            [c for r in subset for c in r.atlas_citations]
        )
    out["atlas_ideas_with_no_evidence"] = sum(not r.atlas_citations for r in results)

    stages: dict[str, Any] = {}
    for stage in STAGES:
        runs = [s for r in results for s in r.stages if s.stage == stage]
        calls = [
            c for r in results for c in r.calls if c.stage == stage and not c.error
        ]
        stages[stage] = {
            "reached": len(runs),
            "first_try_pct": _pct(
                sum(s.succeeded and s.attempts == 1 for s in runs), len(runs)
            ),
            "eventual_pct": _pct(sum(s.succeeded for s in runs), len(runs)),
            "calls": len(calls),
            "latency_s_p50": _p([c.latency_s for c in calls], 0.5),
            "latency_s_p95": _p([c.latency_s for c in calls], 0.95),
            "prompt_tokens_mean": round(
                statistics.mean([c.prompt_tokens for c in calls])
            )
            if calls
            else 0,
            "prompt_tokens_max": max((c.prompt_tokens for c in calls), default=0),
            "completion_tokens_mean": round(
                statistics.mean([c.completion_tokens for c in calls])
            )
            if calls
            else 0,
        }
    out["stages"] = stages
    finished = [
        r
        for r in results
        if len(r.stages) == len(STAGES) and all(s.succeeded for s in r.stages)
    ]
    out["projects_completed_pct"] = _pct(len(finished), len(results))
    out["per_project"] = {
        "wall_s_median": _p([r.atlas_wall_s for r in finished], 0.5),
        "model_calls_median": _p([float(len(r.calls)) for r in finished], 0.5),
        "tokens_median": _p(
            [
                float(sum(c.prompt_tokens + c.completion_tokens for c in r.calls))
                for r in finished
            ],
            0.5,
        ),
        "knowledge_candidates_median": _p(
            [float(r.knowledge_candidates) for r in finished], 0.5
        ),
    }
    out["plain_prompt"] = {
        "latency_s_p50": _p([r.baseline_latency_s for r in results], 0.5),
        "prompt_tokens_mean": round(
            statistics.mean([r.baseline_tokens.get("prompt", 0) for r in results])
        )
        if results
        else 0,
        "completion_tokens_mean": round(
            statistics.mean([r.baseline_tokens.get("completion", 0) for r in results])
        )
        if results
        else 0,
        "errors": sum(bool(r.baseline_error) for r in results),
    }
    out["max_prompt_tokens_seen"] = max(
        (c.prompt_tokens for r in results for c in r.calls), default=0
    )
    out["failed_calls"] = sum(bool(c.error) for r in results for c in r.calls)
    return out


if __name__ == "__main__":
    sys.exit(main())
