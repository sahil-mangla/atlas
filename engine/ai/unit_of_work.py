"""Filesystem-friendly rollback support for proposal commits."""

from collections.abc import Iterable
from typing import Any
from uuid import UUID


class ProposalCommitUnitOfWork:
    """Restores aggregate snapshots when a proposal transformation fails.

    This is a compensating filesystem unit of work, not a database transaction.
    Repositories that create a new aggregate must provide ``delete(project_id)``.
    """

    def __init__(self, project_id: UUID, repositories: Iterable[Any]) -> None:
        self.project_id = project_id
        self.repositories = tuple(repositories)
        self._backups: list[tuple[Any, Any | None]] = []

    def begin(self) -> None:
        """Capture isolated aggregate copies before transformation begins."""
        self._backups = []
        for repository in self.repositories:
            aggregate = repository.get_by_project_id(self.project_id)
            backup = aggregate.model_copy(deep=True) if aggregate else None
            self._backups.append((repository, backup))

    def rollback(self) -> None:
        """Restore all aggregates to their captured filesystem state."""
        for repository, backup in self._backups:
            if backup is not None:
                repository.save(backup)
            else:
                if repository.get_by_project_id(self.project_id) is None:
                    continue
                delete = getattr(repository, "delete", None)
                if delete is None:
                    raise RuntimeError(
                        "Repository cannot remove a newly-created aggregate during rollback."
                    )
                delete(self.project_id)
