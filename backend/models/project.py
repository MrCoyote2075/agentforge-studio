"""
AgentForge Studio - Project Models.

This module defines Pydantic models for project management,
including project stages, requirements, plans, and generated files.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ProjectStage(str, Enum):
    """Stages of a project in the workflow."""

    INITIALIZED = "initialized"
    REQUIREMENTS_GATHERING = "requirements_gathering"
    REQUIREMENTS_CONFIRMED = "requirements_confirmed"
    PLANNING = "planning"
    PLAN_APPROVED = "plan_approved"
    DEVELOPMENT = "development"
    DEVELOPMENT_COMPLETE = "development_complete"
    REVIEW = "review"
    TESTING = "testing"
    READY_FOR_DELIVERY = "ready_for_delivery"
    DELIVERED = "delivered"
    FAILED = "failed"


class ProjectRequirements(BaseModel):
    """
    Model for project requirements.

    Attributes:
        original_request: The original client request.
        clarified_requirements: Clarified requirements after discussion.
        features: List of features to implement.
        constraints: Technical or business constraints.
        confirmed: Whether requirements have been confirmed.
        confirmed_at: When requirements were confirmed.
    """

    original_request: str = Field(..., description="Original client request")
    clarified_requirements: str = Field(
        default="", description="Clarified requirements after discussion"
    )
    features: list[str] = Field(
        default_factory=list, description="List of features to implement"
    )
    constraints: list[str] = Field(
        default_factory=list, description="Technical or business constraints"
    )
    confirmed: bool = Field(default=False, description="Whether requirements confirmed")
    confirmed_at: datetime | None = Field(
        default=None, description="When requirements were confirmed"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "original_request": "I need a portfolio website",
                "clarified_requirements": "A responsive portfolio with 5 sections",
                "features": ["hero section", "about page", "contact form"],
                "constraints": ["must be responsive", "no backend required"],
                "confirmed": True,
            }
        }
    }


class PlanTask(BaseModel):
    """
    Model for a task in the development plan.

    Attributes:
        id: Unique task identifier.
        description: Task description.
        assigned_to: Agent responsible for this task.
        dependencies: List of task IDs this task depends on.
        estimated_complexity: Estimated complexity level.
        file_path: Path to the file to be created/modified.
    """

    id: str = Field(default_factory=lambda: str(uuid4()), description="Task ID")
    description: str = Field(..., description="Task description")
    assigned_to: str = Field(..., description="Agent assigned to this task")
    dependencies: list[str] = Field(
        default_factory=list, description="Task IDs this depends on"
    )
    estimated_complexity: str = Field(
        default="medium", description="Estimated complexity"
    )
    file_path: str | None = Field(
        default=None, description="Path to file to create/modify"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "task-1",
                "description": "Create HTML structure",
                "assigned_to": "FrontendAgent",
                "dependencies": [],
                "estimated_complexity": "medium",
                "file_path": "index.html",
            }
        }
    }


class DevelopmentPlan(BaseModel):
    """
    Model for the development plan.

    Attributes:
        project_name: Name of the project.
        description: Project description.
        technologies: List of technologies to use.
        file_structure: Mapping of directories to files.
        tasks: List of tasks to execute.
        estimated_complexity: Overall complexity estimate.
        approved: Whether the plan has been approved.
        approved_at: When the plan was approved.
    """

    project_name: str = Field(..., description="Project name")
    description: str = Field(default="", description="Project description")
    technologies: list[str] = Field(
        default_factory=list, description="Technologies to use"
    )
    file_structure: dict[str, list[str]] = Field(
        default_factory=dict, description="Directory to files mapping"
    )
    tasks: list[PlanTask] = Field(
        default_factory=list, description="Tasks to execute"
    )
    estimated_complexity: str = Field(
        default="medium", description="Overall complexity"
    )
    approved: bool = Field(default=False, description="Whether plan is approved")
    approved_at: datetime | None = Field(
        default=None, description="When plan was approved"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "project_name": "Portfolio Website",
                "description": "A responsive portfolio website",
                "technologies": ["HTML5", "CSS3", "JavaScript"],
                "file_structure": {
                    "root": ["index.html", "styles.css"],
                    "js": ["script.js"],
                },
                "tasks": [],
                "estimated_complexity": "medium",
                "approved": False,
            }
        }
    }


class GeneratedFile(BaseModel):
    """
    Model for a generated file.

    Attributes:
        path: Relative path of the file.
        content: File content.
        file_type: Type of file (html, css, js, etc).
        generated_by: Agent that generated the file.
        generated_at: When the file was generated.
        reviewed: Whether the file has been reviewed.
        review_notes: Notes from the reviewer.
    """

    path: str = Field(..., description="Relative file path")
    content: str = Field(..., description="File content")
    file_type: str = Field(default="", description="File type")
    generated_by: str = Field(default="", description="Agent that generated the file")
    generated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Generation timestamp"
    )
    reviewed: bool = Field(default=False, description="Whether file was reviewed")
    review_notes: str | None = Field(
        default=None, description="Notes from code review"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "path": "index.html",
                "content": "<!DOCTYPE html>...",
                "file_type": "html",
                "generated_by": "FrontendAgent",
                "reviewed": False,
            }
        }
    }


class Project(BaseModel):
    """
    Full project model with all details.

    Attributes:
        id: Unique project identifier.
        name: Project name.
        description: Project description.
        stage: Current project stage.
        requirements: Project requirements.
        plan: Development plan.
        files: Generated files.
        conversation_history: Chat history with client.
        created_at: When the project was created.
        updated_at: Last update timestamp.
        completed_at: When the project was completed.
        error: Error message if project failed.
        metadata: Additional project metadata.
    """

    id: str = Field(default_factory=lambda: str(uuid4()), description="Project ID")
    name: str = Field(..., description="Project name")
    description: str = Field(default="", description="Project description")
    stage: ProjectStage = Field(
        default=ProjectStage.INITIALIZED, description="Current stage"
    )
    requirements: ProjectRequirements | None = Field(
        default=None, description="Project requirements"
    )
    plan: DevelopmentPlan | None = Field(
        default=None, description="Development plan"
    )
    files: list[GeneratedFile] = Field(
        default_factory=list, description="Generated files"
    )
    conversation_history: list[dict[str, Any]] = Field(
        default_factory=list, description="Chat history"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime | None = Field(
        default=None, description="Last update timestamp"
    )
    completed_at: datetime | None = Field(
        default=None, description="Completion timestamp"
    )
    error: str | None = Field(default=None, description="Error message if failed")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    model_config = {
        "use_enum_values": True,
        "json_schema_extra": {
            "example": {
                "id": "proj-001",
                "name": "Portfolio Website",
                "description": "A responsive portfolio website",
                "stage": "initialized",
            }
        },
    }


class ProjectSummary(BaseModel):
    """
    Summary view of a project for listings.

    Attributes:
        id: Project ID.
        name: Project name.
        stage: Current stage.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
        file_count: Number of generated files.
    """

    id: str = Field(..., description="Project ID")
    name: str = Field(..., description="Project name")
    stage: ProjectStage = Field(..., description="Current stage")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime | None = Field(
        default=None, description="Last update timestamp"
    )
    file_count: int = Field(default=0, description="Number of generated files")

    model_config = {
        "use_enum_values": True,
        "json_schema_extra": {
            "example": {
                "id": "proj-001",
                "name": "Portfolio Website",
                "stage": "development",
                "created_at": "2024-01-15T10:30:00Z",
                "file_count": 5,
            }
        },
    }
