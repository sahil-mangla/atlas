"""Explicit command-name -> Command class registry for the eval runner.

Mirrors the "explicit, literal, no reflection" table style used by
``atlas._service._COMMAND_CAPABILITY`` and ``atlas.contracts.errors._ERROR_CODE_MAP``.
"""

from __future__ import annotations

from atlas.commands import (
    ApproveProposalCommand,
    ArchiveProjectCommand,
    Command,
    CompleteObjectiveCommand,
    CreateProjectCommand,
    ExecuteStageCommand,
    GetWorkflowStatusCommand,
    ListKnowledgeCandidatesCommand,
    ListProjectsCommand,
    LoadProjectCommand,
    RejectProposalCommand,
    ReviewKnowledgeCandidateCommand,
    ShowKnowledgeCandidateCommand,
    TransitionStageCommand,
)


class UnknownCommand(Command):
    """A syntactically valid Command that no capability handles.

    Constructed for tasks using the "__unknown_command__" sentinel type, to
    exercise Atlas.handle()'s UNKNOWN_ERROR defensive path -- mirrors
    tests/test_atlas/test_platform_handle.py::test_handle_unrecognized_command_type.
    """


#: Sentinel task-file type name resolving to UnknownCommand.
UNKNOWN_COMMAND_TYPE = "__unknown_command__"

COMMAND_REGISTRY: dict[str, type[Command]] = {
    "CreateProjectCommand": CreateProjectCommand,
    "LoadProjectCommand": LoadProjectCommand,
    "ListProjectsCommand": ListProjectsCommand,
    "ArchiveProjectCommand": ArchiveProjectCommand,
    "ExecuteStageCommand": ExecuteStageCommand,
    "ApproveProposalCommand": ApproveProposalCommand,
    "RejectProposalCommand": RejectProposalCommand,
    "TransitionStageCommand": TransitionStageCommand,
    "CompleteObjectiveCommand": CompleteObjectiveCommand,
    "GetWorkflowStatusCommand": GetWorkflowStatusCommand,
    "ReviewKnowledgeCandidateCommand": ReviewKnowledgeCandidateCommand,
    "ListKnowledgeCandidatesCommand": ListKnowledgeCandidatesCommand,
    "ShowKnowledgeCandidateCommand": ShowKnowledgeCandidateCommand,
    UNKNOWN_COMMAND_TYPE: UnknownCommand,
}


class UnregisteredCommandTypeError(Exception):
    """Raised when a task references a command type name the registry
    doesn't know at all -- a task-authoring bug, distinct from the
    deliberate ``UnknownCommand`` sentinel."""


def resolve_command_class(type_name: str) -> type[Command]:
    command_class = COMMAND_REGISTRY.get(type_name)
    if command_class is None:
        raise UnregisteredCommandTypeError(
            f"No command registered for task-file type {type_name!r}. "
            f"Known types: {sorted(COMMAND_REGISTRY)}"
        )
    return command_class
