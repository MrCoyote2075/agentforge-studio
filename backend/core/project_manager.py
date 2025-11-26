"""
AgentForge Studio - Project Manager.

This module implements project data management functionality,
handling project creation, updates, and file management.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from backend.models.project import (
    DevelopmentPlan,
    GeneratedFile,
    Project,
    ProjectRequirements,
    ProjectStage,
    ProjectSummary,
)


class ProjectManager:
    """
    Manager for project data and file storage.

    This class handles all project-related data operations including
    creation, updates, requirements storage, plan management, and
    generated file tracking.

    Attributes:
        projects: Dictionary of projects by ID.
        logger: Logger instance.

    Example:
        >>> manager = ProjectManager()
        >>> project = manager.create_project("Portfolio Website", "A responsive site")
        >>> manager.add_file(project.id, "index.html", "<html>...")
    """

    def __init__(self) -> None:
        """Initialize the project manager."""
        self._projects: dict[str, Project] = {}
        self.logger = logging.getLogger("project_manager")

    def create_project(
        self,
        name: str,
        description: str = "",
    ) -> Project:
        """
        Create a new project.

        Args:
            name: Project name.
            description: Project description.

        Returns:
            The created project.
        """
        project_id = str(uuid4())
        project = Project(
            id=project_id,
            name=name,
            description=description,
            stage=ProjectStage.INITIALIZED,
            created_at=datetime.utcnow(),
        )
        self._projects[project_id] = project

        self.logger.info(f"Created project '{name}' with ID {project_id}")
        return project

    def store_project(self, project: Project) -> None:
        """
        Store an existing project instance.

        Args:
            project: Project instance to store.
        """
        self._projects[project.id] = project
        self.logger.info(f"Stored project '{project.name}' with ID {project.id}")

    def get_project(self, project_id: str) -> Project | None:
        """
        Get a project by ID.

        Args:
            project_id: Project identifier.

        Returns:
            The project or None if not found.
        """
        return self._projects.get(project_id)

    def update_requirements(
        self,
        project_id: str,
        requirements: ProjectRequirements,
    ) -> bool:
        """
        Update project requirements.

        Args:
            project_id: Project identifier.
            requirements: The requirements to store.

        Returns:
            True if successful, False if project not found.
        """
        project = self._projects.get(project_id)
        if not project:
            self.logger.warning(f"Project {project_id} not found")
            return False

        project.requirements = requirements
        project.updated_at = datetime.utcnow()

        self.logger.info(f"Updated requirements for project {project_id}")
        return True

    def confirm_requirements(self, project_id: str) -> bool:
        """
        Mark requirements as confirmed.

        Args:
            project_id: Project identifier.

        Returns:
            True if successful, False if project or requirements not found.
        """
        project = self._projects.get(project_id)
        if not project or not project.requirements:
            return False

        project.requirements.confirmed = True
        project.requirements.confirmed_at = datetime.utcnow()
        project.updated_at = datetime.utcnow()

        self.logger.info(f"Confirmed requirements for project {project_id}")
        return True

    def update_plan(
        self,
        project_id: str,
        plan: DevelopmentPlan,
    ) -> bool:
        """
        Update project development plan.

        Args:
            project_id: Project identifier.
            plan: The development plan to store.

        Returns:
            True if successful, False if project not found.
        """
        project = self._projects.get(project_id)
        if not project:
            self.logger.warning(f"Project {project_id} not found")
            return False

        project.plan = plan
        project.updated_at = datetime.utcnow()

        self.logger.info(f"Updated plan for project {project_id}")
        return True

    def approve_plan(self, project_id: str) -> bool:
        """
        Mark the development plan as approved.

        Args:
            project_id: Project identifier.

        Returns:
            True if successful, False if project or plan not found.
        """
        project = self._projects.get(project_id)
        if not project or not project.plan:
            return False

        project.plan.approved = True
        project.plan.approved_at = datetime.utcnow()
        project.updated_at = datetime.utcnow()

        self.logger.info(f"Approved plan for project {project_id}")
        return True

    def add_file(
        self,
        project_id: str,
        path: str,
        content: str,
        file_type: str = "",
        generated_by: str = "",
    ) -> GeneratedFile | None:
        """
        Add a generated file to the project.

        Args:
            project_id: Project identifier.
            path: Relative file path.
            content: File content.
            file_type: Type of file (html, css, js, etc.).
            generated_by: Name of the agent that generated the file.

        Returns:
            The created GeneratedFile or None if project not found.
        """
        project = self._projects.get(project_id)
        if not project:
            self.logger.warning(f"Project {project_id} not found")
            return None

        # Infer file type from extension if not provided
        if not file_type and "." in path:
            file_type = path.rsplit(".", 1)[-1]

        generated_file = GeneratedFile(
            path=path,
            content=content,
            file_type=file_type,
            generated_by=generated_by,
            generated_at=datetime.utcnow(),
        )

        # Check if file already exists and update it
        for i, existing in enumerate(project.files):
            if existing.path == path:
                project.files[i] = generated_file
                self.logger.info(f"Updated file {path} for project {project_id}")
                project.updated_at = datetime.utcnow()
                return generated_file

        project.files.append(generated_file)
        project.updated_at = datetime.utcnow()

        self.logger.info(f"Added file {path} to project {project_id}")
        return generated_file

    def update_file(
        self,
        project_id: str,
        path: str,
        content: str,
    ) -> bool:
        """
        Update an existing file's content.

        Args:
            project_id: Project identifier.
            path: File path.
            content: New content.

        Returns:
            True if successful, False if project or file not found.
        """
        project = self._projects.get(project_id)
        if not project:
            return False

        for file in project.files:
            if file.path == path:
                file.content = content
                file.generated_at = datetime.utcnow()
                project.updated_at = datetime.utcnow()
                self.logger.info(f"Updated file {path} for project {project_id}")
                return True

        return False

    def mark_file_reviewed(
        self,
        project_id: str,
        path: str,
        review_notes: str = "",
    ) -> bool:
        """
        Mark a file as reviewed.

        Args:
            project_id: Project identifier.
            path: File path.
            review_notes: Notes from the reviewer.

        Returns:
            True if successful, False if project or file not found.
        """
        project = self._projects.get(project_id)
        if not project:
            return False

        for file in project.files:
            if file.path == path:
                file.reviewed = True
                file.review_notes = review_notes
                project.updated_at = datetime.utcnow()
                return True

        return False

    def get_file(
        self,
        project_id: str,
        path: str,
    ) -> GeneratedFile | None:
        """
        Get a specific file from the project.

        Args:
            project_id: Project identifier.
            path: File path.

        Returns:
            The file or None if not found.
        """
        project = self._projects.get(project_id)
        if not project:
            return None

        for file in project.files:
            if file.path == path:
                return file
        return None

    def get_files(self, project_id: str) -> list[GeneratedFile]:
        """
        Get all files for a project.

        Args:
            project_id: Project identifier.

        Returns:
            List of generated files.
        """
        project = self._projects.get(project_id)
        if not project:
            return []
        return project.files

    def delete_file(self, project_id: str, path: str) -> bool:
        """
        Delete a file from the project.

        Args:
            project_id: Project identifier.
            path: File path.

        Returns:
            True if file was deleted, False if not found.
        """
        project = self._projects.get(project_id)
        if not project:
            return False

        for i, file in enumerate(project.files):
            if file.path == path:
                del project.files[i]
                project.updated_at = datetime.utcnow()
                self.logger.info(f"Deleted file {path} from project {project_id}")
                return True
        return False

    def add_conversation_message(
        self,
        project_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Add a message to the project's conversation history.

        Args:
            project_id: Project identifier.
            role: Message role (user, assistant).
            content: Message content.
            metadata: Optional metadata.

        Returns:
            True if successful, False if project not found.
        """
        project = self._projects.get(project_id)
        if not project:
            return False

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if metadata:
            message["metadata"] = metadata

        project.conversation_history.append(message)
        project.updated_at = datetime.utcnow()
        return True

    def list_projects(self) -> list[ProjectSummary]:
        """
        List all projects as summaries.

        Returns:
            List of project summaries.
        """
        summaries = []
        for project in self._projects.values():
            summary = ProjectSummary(
                id=project.id,
                name=project.name,
                stage=ProjectStage(project.stage),
                created_at=project.created_at,
                updated_at=project.updated_at,
                file_count=len(project.files),
            )
            summaries.append(summary)
        return summaries

    def update_stage(self, project_id: str, stage: ProjectStage) -> bool:
        """
        Update the project stage.

        Args:
            project_id: Project identifier.
            stage: New stage.

        Returns:
            True if successful, False if project not found.
        """
        project = self._projects.get(project_id)
        if not project:
            return False

        project.stage = stage
        project.updated_at = datetime.utcnow()

        if stage == ProjectStage.DELIVERED:
            project.completed_at = datetime.utcnow()

        return True

    def set_error(self, project_id: str, error: str) -> bool:
        """
        Set an error message on the project.

        Args:
            project_id: Project identifier.
            error: Error message.

        Returns:
            True if successful, False if project not found.
        """
        project = self._projects.get(project_id)
        if not project:
            return False

        project.error = error
        project.stage = ProjectStage.FAILED
        project.updated_at = datetime.utcnow()
        return True

    def delete_project(self, project_id: str) -> bool:
        """
        Delete a project.

        Args:
            project_id: Project identifier.

        Returns:
            True if deleted, False if not found.
        """
        if project_id in self._projects:
            del self._projects[project_id]
            self.logger.info(f"Deleted project {project_id}")
            return True
        return False

    def clear(self) -> None:
        """Clear all projects."""
        self._projects.clear()
        self.logger.info("Project manager cleared")
