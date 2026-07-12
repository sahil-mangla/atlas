"""Filesystem implementation of the Planning repository."""

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from engine.domain.planning import Planning
from engine.planning.repository import PlanningRepository
from engine.planning.serializers import deserialize_planning, serialize_planning


class FilesystemPlanningRepository(PlanningRepository):
    """Stores Planning records in .atlas/planning.json."""

    def __init__(self, workspace_root: Path) -> None:
        """Initialize the filesystem repository.

        Args:
            workspace_root: Path to the workspace root directory.
        """
        self.workspace_root = workspace_root
        self.atlas_dir = workspace_root / ".atlas"
        self.file_path = self.atlas_dir / "planning.json"

    def _ensure_dir(self) -> None:
        """Ensure the .atlas directory exists."""
        if not self.atlas_dir.exists():
            self.atlas_dir.mkdir(parents=True, exist_ok=True)

    def _read_all(self) -> dict[str, Any]:
        """Read all planning from storage."""
        if not self.file_path.exists():
            return {}
        try:
            content = self.file_path.read_text(encoding="utf-8")
            if not content.strip():
                return {}
            return json.loads(content)
        except Exception:
            return {}

    def _write_all(self, data: dict[str, Any]) -> None:
        """Write all planning to storage."""
        self._ensure_dir()
        self.file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def save(self, planning: Planning) -> None:
        """Persist a Planning aggregate to storage."""
        all_data = self._read_all()
        all_data[str(planning.project_id)] = serialize_planning(planning)
        self._write_all(all_data)

    def get_by_project_id(self, project_id: UUID) -> Planning | None:
        """Retrieve Planning by its owning project ID."""
        all_data = self._read_all()
        data = all_data.get(str(project_id))
        if data is None:
            return None
        return deserialize_planning(data)

    def exists(self, project_id: UUID) -> bool:
        """Check if Planning exists for a project."""
        return str(project_id) in self._read_all()
