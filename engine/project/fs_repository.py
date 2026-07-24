"""Filesystem-backed implementation of the ProjectRepository."""

import json
import re
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError

from engine.domain.project import Project
from engine.project.exceptions import (
    InvalidProjectException,
    ProjectAlreadyExistsException,
    ProjectNotFoundException,
)
from engine.project.repository import ProjectRepository
from shared.atomic_write import atomic_write_text


class FilesystemProjectRepository(ProjectRepository):
    """Filesystem repository for persisting projects in a local workspace directory.

    Under the hybrid model, each project directory contains a `.atlas/` folder
    with a `project.json` file. The repository maps project UUIDs to their
    physical directories by dynamically scanning the workspace.
    """

    def __init__(self, base_dir: Path) -> None:
        """Initialize the repository with a base directory for all projects.

        Args:
            base_dir: The root directory where projects are stored.
        """
        self.base_dir = base_dir
        self._project_paths: dict[UUID, Path] = {}
        self._scan_workspace()

    def _scan_workspace(self) -> None:
        """Scan the base directory to discover all existing projects."""
        if not self.base_dir.exists():
            return

        for path in self.base_dir.iterdir():
            if path.is_dir():
                metadata_file = path / ".atlas" / "project.json"
                if metadata_file.is_file():
                    try:
                        project = self._load_from_file(metadata_file)
                        self._project_paths[project.id] = path
                    except (InvalidProjectException, ValidationError):
                        # Skip corrupt project metadata during scanning
                        continue

    def _slugify(self, name: str) -> str:
        """Convert a project name into a filesystem-safe directory name."""
        slug = name.lower().strip()
        slug = re.sub(r"[^\w\s-]", "", slug)
        return re.sub(r"[-\s]+", "-", slug)

    def _load_from_file(self, file_path: Path) -> Project:
        """Read and deserialize a Project from a json file.

        Args:
            file_path: The Path to the project.json file.

        Returns:
            The deserialized Project.

        Raises:
            InvalidProjectException: If the file is corrupt or invalid.
        """
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return Project(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise InvalidProjectException(
                f"Failed to parse project metadata at {file_path}: {e}"
            ) from e
        except OSError as e:
            raise InvalidProjectException(
                f"Failed to read project metadata file at {file_path}: {e}"
            ) from e

    def _save_to_file(self, project: Project, file_path: Path) -> None:
        """Serialize and write a Project to a json file.

        Args:
            project: The Project domain model.
            file_path: The file path to write to.
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            data = project.model_dump(mode="json")
            atomic_write_text(file_path, json.dumps(data, indent=4))
        except OSError as e:
            raise InvalidProjectException(
                f"Failed to write project metadata to {file_path}: {e}"
            ) from e

    def register_path(self, project_id: UUID, path: Path) -> None:
        """Manually register a project's directory path.

        Used when creating a project at a specific custom location.

        Args:
            project_id: The UUID of the project.
            path: The directory path where the project resides.
        """
        self._project_paths[project_id] = path

    def save(self, project: Project) -> None:
        """Persist or update the project metadata.

        If the project is new and has no registered path, a default path
        is created under the base directory using a slugified project name.

        Args:
            project: The Project domain model.
        """
        path = self._project_paths.get(project.id)

        if not path:
            # Generate default directory name
            slug = self._slugify(project.name)
            path = self.base_dir / slug

            # Check if directory already exists with another project
            metadata_file = path / ".atlas" / "project.json"
            if metadata_file.is_file():
                try:
                    existing = self._load_from_file(metadata_file)
                    if existing.id != project.id:
                        raise ProjectAlreadyExistsException(
                            f"Project directory '{path}' already contains "
                            "another project."
                        )
                except InvalidProjectException as e:
                    # If corrupt, overwrite or raise error; here we play safe
                    raise ProjectAlreadyExistsException(
                        f"Directory '{path}' already exists and contains "
                        "corrupt project data."
                    ) from e

            self._project_paths[project.id] = path

        metadata_file = path / ".atlas" / "project.json"
        self._save_to_file(project, metadata_file)

    def get_by_id(self, project_id: UUID) -> Project | None:
        """Retrieve a project by its unique identifier.

        Args:
            project_id: The UUID of the project.

        Returns:
            The Project domain model if found, otherwise None.
        """
        path = self._project_paths.get(project_id)
        if not path:
            # Rescan in case project was added externally
            self._scan_workspace()
            path = self._project_paths.get(project_id)

        if not path:
            return None

        metadata_file = path / ".atlas" / "project.json"
        if not metadata_file.is_file():
            # Directory was deleted externally
            del self._project_paths[project_id]
            return None

        return self._load_from_file(metadata_file)

    def discover(self) -> list[Project]:
        """Rescan workspace and return all discovered Projects.

        Returns:
            A list of discovered Project domain models.
        """
        self._scan_workspace()
        projects: list[Project] = []
        for project_id in list(self._project_paths.keys()):
            project = self.get_by_id(project_id)
            if project:
                projects.append(project)
        return projects

    def get_project_path(self, project_id: UUID) -> Path:
        """Helper to retrieve the physical directory path of a project.

        Args:
            project_id: The UUID of the project.

        Returns:
            The Path to the project directory.

        Raises:
            ProjectNotFoundException: If the project is not tracked.
        """
        path = self._project_paths.get(project_id)
        if not path:
            raise ProjectNotFoundException(
                f"Project with ID {project_id} is not tracked by the repository."
            )
        return path

    def delete(self, project_id: UUID) -> None:
        """Remove the project's metadata file and deregister its path.

        Only removes ``project.json`` -- not the project's directory tree,
        which may pre-exist at a caller-supplied custom path and hold
        unrelated content.
        """
        path = self._project_paths.pop(project_id, None)
        if path is None:
            return
        metadata_file = path / ".atlas" / "project.json"
        try:
            metadata_file.unlink(missing_ok=True)
        except OSError as e:
            raise InvalidProjectException(
                f"Failed to remove project metadata at {metadata_file}: {e}"
            ) from e
