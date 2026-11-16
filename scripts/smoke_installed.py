"""Smoke-test an *installed* ATLAS: run the whole pipeline offline.

Used by CI after ``pip install dist/*.whl`` into a clean environment, and
usable by hand to check any install:

    python scripts/smoke_installed.py            # uses `atlas` from PATH
    python scripts/smoke_installed.py /path/to/atlas

It imports nothing from the repository, runs in a fresh temporary directory,
and uses the SCRIPTED protocol, so it needs no API key and no network.
Exits non-zero on the first failure.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
STAGES = ("research", "planning", "architecture", "review")


def main() -> int:
    """Drive the installed CLI through every AI stage."""
    atlas = sys.argv[1] if len(sys.argv) > 1 else shutil.which("atlas")
    if not atlas:
        sys.stderr.write("atlas executable not found on PATH\n")
        return 1

    workdir = tempfile.mkdtemp(prefix="atlas-smoke-")
    env = dict(os.environ)
    env.update({"ATLAS_AI_PROTOCOL": "SCRIPTED", "PYTHONIOENCODING": "utf-8"})

    def run(*args: str) -> str:
        completed = subprocess.run(
            [atlas, *args],
            cwd=workdir,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            check=False,
        )
        sys.stdout.write(f"$ atlas {' '.join(args)}\n")
        if completed.returncode != 0:
            sys.stderr.write(completed.stdout + completed.stderr)
            raise SystemExit(f"FAILED (exit {completed.returncode})")
        return completed.stdout

    def first_uuid(text: str) -> str:
        match = UUID.search(text)
        if not match:
            raise SystemExit(f"FAILED: no ID in output:\n{text}")
        return match.group()

    run("version")
    project = (
        "--project-id",
        first_uuid(
            run(
                "project",
                "create",
                "--name",
                "Smoke",
                "--description",
                "Installed-package smoke test.",
                "--objective",
                "Run every stage offline.",
            )
        ),
    )
    run("workflow", "transition", *project, "--reason", "start")
    for stage in STAGES:
        proposal = first_uuid(run("stage", "execute", *project, "--stage", stage))
        run("proposal", "approve", *project, "--proposal-id", proposal)
    run("knowledge", "list", *project)
    status = run("presentation", "dashboard", *project, "--format", "json")
    if "iteration" not in status:
        raise SystemExit(f"FAILED: project did not reach iteration:\n{status}")

    shutil.rmtree(workdir, ignore_errors=True)
    sys.stdout.write("OK: installed ATLAS ran the full pipeline offline.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
