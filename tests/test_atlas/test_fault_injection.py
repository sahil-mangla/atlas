"""Fault injection through the public SDK: a disk failure mid-commit.

Approving a proposal writes several files. If the disk fails partway, the
project must be left exactly as it was -- no half-written aggregate, no stray
temp files -- and the same approval must succeed once the fault clears.
"""

from pathlib import Path

import pytest

from atlas import Atlas
from atlas.commands import (
    ApproveProposalCommand,
    CreateProjectCommand,
    ExecuteStageCommand,
    TransitionStageCommand,
)
from atlas.testing import create_test_platform
from atlas.types import WorkflowStage


def _snapshot(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


@pytest.fixture
def platform(tmp_path: Path) -> Atlas:
    return create_test_platform(tmp_path, instrumentation_enabled=False)


# Approving a research proposal performs ten file replacements. The first
# four write the research aggregate and are covered by the commit's rollback.
_ROLLED_BACK_WRITES = range(1, 5)
# The rest (workflow, knowledge, project, proposal record) happen after the
# snapshot is committed and are not rolled back. Measured behaviour today:
# the project is left partly updated and the approval cannot be retried; a
# failed workflow write (8) is even reported as success, and a failed
# proposal-record write (10) escapes as a raw OSError.
_UNPROTECTED_WRITES = range(5, 11)
_KNOWN_BUG = pytest.mark.xfail(
    strict=True,
    reason=(
        "Known bug: approval is only atomic for the stage aggregate. A write "
        "failure after the snapshot commit leaves partial state that a retry "
        "cannot recover."
    ),
)


@pytest.mark.parametrize(
    "fail_on_write",
    [
        *_ROLLED_BACK_WRITES,
        *(pytest.param(n, marks=_KNOWN_BUG) for n in _UNPROTECTED_WRITES),
    ],
)
def test_disk_failure_during_approval_leaves_project_untouched_and_retryable(
    platform: Atlas,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fail_on_write: int,
) -> None:
    project = platform.create_project(
        CreateProjectCommand(name="Faulty Disk", description="d", objective="o")
    )
    platform.transition_stage(TransitionStageCommand(project_id=project.id))
    proposal = platform.execute_stage(
        ExecuteStageCommand(project_id=project.id, stage=WorkflowStage.RESEARCH)
    )
    approve = ApproveProposalCommand(project_id=project.id, proposal_id=proposal.id)
    before = _snapshot(tmp_path)

    real_replace = Path.replace
    writes = 0

    def failing_replace(self: Path, target: Path) -> Path:
        nonlocal writes
        writes += 1
        if writes == fail_on_write:
            raise OSError(28, "No space left on device")
        return real_replace(self, target)

    with monkeypatch.context() as patched:
        patched.setattr(Path, "replace", failing_replace)
        try:
            result = platform.approve_proposal(approve)
        except Exception:
            result = None
    assert writes >= fail_on_write, "the fault was never reached"
    assert result is None or not result.success

    assert not list(tmp_path.rglob("*.tmp")), "temp files left behind"
    assert _snapshot(tmp_path) == before

    retried = platform.approve_proposal(approve)
    assert retried.success
