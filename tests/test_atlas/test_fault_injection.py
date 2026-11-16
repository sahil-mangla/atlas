"""Fault injection through the public SDK: a disk failure mid-approval.

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
    GetWorkflowStatusCommand,
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


# Approving a research proposal performs twelve file replacements: the
# research aggregate (1-4), workflow (5), knowledge (6-7), the stage
# transition (8), the project record (9) and the proposal record (10-12).
_WRITES_DURING_APPROVAL = range(1, 13)
# A failed stage-transition write is the one case that is not rolled back: the
# proposal is committed and the result reports the transition as blocked, so
# the user advances the stage by hand once the disk recovers.
_TRANSITION_WRITE = 8


@pytest.mark.parametrize("fail_on_write", _WRITES_DURING_APPROVAL)
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

    if fail_on_write == _TRANSITION_WRITE:
        assert result is not None
        assert result.success
        assert result.transition_blocked
        platform.transition_stage(TransitionStageCommand(project_id=project.id))
    else:
        assert result is None or not result.success
        assert not list(tmp_path.rglob("*.tmp")), "temp files left behind"
        assert _snapshot(tmp_path) == before
        assert platform.approve_proposal(approve).success

    status = platform.get_workflow_status(
        GetWorkflowStatusCommand(project_id=project.id)
    )
    assert status.current_stage == WorkflowStage.PLANNING
