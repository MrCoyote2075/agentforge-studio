"""
AgentForge Studio - Workflow Engine.

This module implements a workflow state machine for managing
project stages and transitions throughout the development lifecycle.
"""

import logging
from datetime import datetime
from typing import Any

from backend.models.project import Project, ProjectStage


class WorkflowEngine:
    """
    Workflow state machine for project lifecycle management.

    This class manages the progression of projects through various stages,
    ensuring valid transitions and tracking state changes.

    Attributes:
        projects: Dictionary of projects by ID.
        logger: Logger instance.

    Example:
        >>> engine = WorkflowEngine()
        >>> project = engine.create_project("proj-1", "My Project")
        >>> engine.transition("proj-1", ProjectStage.REQUIREMENTS_GATHERING)
    """

    # Define valid stage transitions
    VALID_TRANSITIONS: dict[ProjectStage, list[ProjectStage]] = {
        ProjectStage.INITIALIZED: [
            ProjectStage.REQUIREMENTS_GATHERING,
            ProjectStage.FAILED,
        ],
        ProjectStage.REQUIREMENTS_GATHERING: [
            ProjectStage.REQUIREMENTS_CONFIRMED,
            ProjectStage.FAILED,
        ],
        ProjectStage.REQUIREMENTS_CONFIRMED: [
            ProjectStage.PLANNING,
            ProjectStage.REQUIREMENTS_GATHERING,  # Can go back for changes
            ProjectStage.FAILED,
        ],
        ProjectStage.PLANNING: [
            ProjectStage.PLAN_APPROVED,
            ProjectStage.REQUIREMENTS_GATHERING,  # Can go back if plan not feasible
            ProjectStage.FAILED,
        ],
        ProjectStage.PLAN_APPROVED: [
            ProjectStage.DEVELOPMENT,
            ProjectStage.PLANNING,  # Can revise plan
            ProjectStage.FAILED,
        ],
        ProjectStage.DEVELOPMENT: [
            ProjectStage.DEVELOPMENT_COMPLETE,
            ProjectStage.FAILED,
        ],
        ProjectStage.DEVELOPMENT_COMPLETE: [
            ProjectStage.REVIEW,
            ProjectStage.DEVELOPMENT,  # Back to dev if issues found
            ProjectStage.FAILED,
        ],
        ProjectStage.REVIEW: [
            ProjectStage.TESTING,
            ProjectStage.DEVELOPMENT,  # Back to dev if review fails
            ProjectStage.FAILED,
        ],
        ProjectStage.TESTING: [
            ProjectStage.READY_FOR_DELIVERY,
            ProjectStage.DEVELOPMENT,  # Back to dev if tests fail
            ProjectStage.FAILED,
        ],
        ProjectStage.READY_FOR_DELIVERY: [
            ProjectStage.DELIVERED,
            ProjectStage.FAILED,
        ],
        ProjectStage.DELIVERED: [],  # Terminal state
        ProjectStage.FAILED: [
            ProjectStage.INITIALIZED,  # Can restart from beginning
        ],
    }

    def __init__(self) -> None:
        """Initialize the workflow engine."""
        self._projects: dict[str, Project] = {}
        self._stage_history: dict[str, list[dict[str, Any]]] = {}
        self.logger = logging.getLogger("workflow_engine")

    def create_project(self, project_id: str, name: str) -> Project:
        """
        Create a new project in the workflow.

        Args:
            project_id: Unique project identifier.
            name: Project name.

        Returns:
            The created project.

        Raises:
            ValueError: If project_id already exists.
        """
        if project_id in self._projects:
            raise ValueError(f"Project with ID {project_id} already exists")

        project = Project(
            id=project_id,
            name=name,
            stage=ProjectStage.INITIALIZED,
        )
        self._projects[project_id] = project
        self._stage_history[project_id] = [
            {
                "stage": ProjectStage.INITIALIZED.value,
                "timestamp": datetime.utcnow().isoformat(),
                "notes": "Project created",
            }
        ]

        self.logger.info(f"Created project '{name}' with ID {project_id}")
        return project

    def get_project(self, project_id: str) -> Project | None:
        """
        Get a project by ID.

        Args:
            project_id: Project identifier.

        Returns:
            The project or None if not found.
        """
        return self._projects.get(project_id)

    def can_transition(self, project_id: str, to_stage: ProjectStage) -> bool:
        """
        Check if a transition to the given stage is valid.

        Args:
            project_id: Project identifier.
            to_stage: Target stage.

        Returns:
            True if transition is valid, False otherwise.
        """
        project = self._projects.get(project_id)
        if not project:
            return False

        current_stage = ProjectStage(project.stage)
        valid_next = self.VALID_TRANSITIONS.get(current_stage, [])
        return to_stage in valid_next

    def transition(
        self,
        project_id: str,
        to_stage: ProjectStage,
        notes: str = "",
    ) -> bool:
        """
        Transition a project to a new stage.

        Args:
            project_id: Project identifier.
            to_stage: Target stage.
            notes: Optional notes about the transition.

        Returns:
            True if transition was successful, False otherwise.
        """
        project = self._projects.get(project_id)
        if not project:
            self.logger.warning(f"Project {project_id} not found")
            return False

        current_stage = ProjectStage(project.stage)

        if not self.can_transition(project_id, to_stage):
            self.logger.warning(
                f"Invalid transition from {current_stage} to {to_stage} "
                f"for project {project_id}"
            )
            return False

        # Update project stage
        project.stage = to_stage
        project.updated_at = datetime.utcnow()

        # Handle terminal states
        if to_stage == ProjectStage.DELIVERED:
            project.completed_at = datetime.utcnow()
        elif to_stage == ProjectStage.FAILED:
            project.error = notes or "Project failed"

        # Record in history
        self._stage_history[project_id].append({
            "stage": to_stage.value,
            "from_stage": current_stage.value,
            "timestamp": datetime.utcnow().isoformat(),
            "notes": notes,
        })

        self.logger.info(
            f"Project {project_id} transitioned: {current_stage} -> {to_stage}"
        )
        return True

    def get_next_stages(self, project_id: str) -> list[ProjectStage]:
        """
        Get valid next stages for a project.

        Args:
            project_id: Project identifier.

        Returns:
            List of valid next stages.
        """
        project = self._projects.get(project_id)
        if not project:
            return []

        current_stage = ProjectStage(project.stage)
        return self.VALID_TRANSITIONS.get(current_stage, [])

    def get_stage_history(self, project_id: str) -> list[dict[str, Any]]:
        """
        Get the stage transition history for a project.

        Args:
            project_id: Project identifier.

        Returns:
            List of stage transitions.
        """
        return self._stage_history.get(project_id, [])

    def get_current_stage(self, project_id: str) -> ProjectStage | None:
        """
        Get the current stage of a project.

        Args:
            project_id: Project identifier.

        Returns:
            Current stage or None if project not found.
        """
        project = self._projects.get(project_id)
        if not project:
            return None
        return ProjectStage(project.stage)

    def is_terminal(self, project_id: str) -> bool:
        """
        Check if a project is in a terminal state.

        Args:
            project_id: Project identifier.

        Returns:
            True if project is in DELIVERED or FAILED state.
        """
        project = self._projects.get(project_id)
        if not project:
            return False

        stage = ProjectStage(project.stage)
        return stage in (ProjectStage.DELIVERED, ProjectStage.FAILED)

    def get_all_projects(self) -> list[Project]:
        """
        Get all projects in the workflow.

        Returns:
            List of all projects.
        """
        return list(self._projects.values())

    def get_projects_by_stage(self, stage: ProjectStage) -> list[Project]:
        """
        Get all projects in a specific stage.

        Args:
            stage: Stage to filter by.

        Returns:
            List of projects in the given stage.
        """
        return [
            p for p in self._projects.values()
            if ProjectStage(p.stage) == stage
        ]

    def remove_project(self, project_id: str) -> bool:
        """
        Remove a project from the workflow.

        Args:
            project_id: Project identifier.

        Returns:
            True if project was removed, False if not found.
        """
        if project_id in self._projects:
            del self._projects[project_id]
            if project_id in self._stage_history:
                del self._stage_history[project_id]
            self.logger.info(f"Removed project {project_id}")
            return True
        return False

    def clear(self) -> None:
        """Clear all projects from the workflow."""
        self._projects.clear()
        self._stage_history.clear()
        self.logger.info("Workflow engine cleared")
