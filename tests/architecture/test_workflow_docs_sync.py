"""RC-005 regression: workflow documentation must stay in sync with
``WorkflowTransitionService.VALID_TRANSITIONS``.

Before this fix, ``docs/architecture/engineering-workflow.md`` and
``docs/diagrams/engineering-pipeline.md`` were both missing the two
"skip an optional manual-detour stage" shortcut edges
(RESEARCH -> PLANNING, ARCHITECTURE -> REVIEW) that the code has actually
supported since Phase 9-ish -- a stale diagram silently drifting from the
state machine it claims to document.
"""

from pathlib import Path

from engine.domain.enums import WorkflowStage
from engine.workflow.services import WorkflowTransitionService

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PIPELINE_DIAGRAM = _REPO_ROOT / "docs" / "diagrams" / "engineering-pipeline.md"
_ENGINEERING_WORKFLOW_DOC = (
    _REPO_ROOT / "docs" / "architecture" / "engineering-workflow.md"
)
_WORKFLOW_STAGES_DOC = _REPO_ROOT / "docs" / "architecture" / "workflow-stages.md"


def _stage_title(stage: WorkflowStage) -> str:
    """Match the diagram's node-naming convention, e.g. 'problem_definition' ->
    'Problem_Definition'."""
    return "_".join(part.capitalize() for part in stage.value.split("_"))


def test_pipeline_diagram_has_an_edge_for_every_valid_transition() -> None:
    content = _PIPELINE_DIAGRAM.read_text()
    for source, targets in WorkflowTransitionService.VALID_TRANSITIONS.items():
        for target in targets:
            edge = f"{_stage_title(source)} --> {_stage_title(target)}"
            assert edge in content, (
                f"{source.value} -> {target.value} is a valid transition "
                f"but has no matching edge in {_PIPELINE_DIAGRAM.name}"
            )


def test_engineering_workflow_doc_lists_every_stage() -> None:
    content = _ENGINEERING_WORKFLOW_DOC.read_text()
    for stage in WorkflowStage:
        title = stage.value.replace("_", " ").title()
        assert title in content, (
            f"WorkflowStage.{stage.name} ('{title}') is not mentioned in "
            f"{_ENGINEERING_WORKFLOW_DOC.name}"
        )


def test_workflow_stages_doc_lists_every_stage() -> None:
    content = _WORKFLOW_STAGES_DOC.read_text()
    for stage in WorkflowStage:
        assert stage.value.upper() in content, (
            f"WorkflowStage.{stage.name} is not mentioned in "
            f"{_WORKFLOW_STAGES_DOC.name}"
        )
