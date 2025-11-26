"""
AgentForge Studio - Pydantic Schemas.

This module defines all the Pydantic models used for data validation,
serialization, and API request/response handling.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Types of messages exchanged between agents."""

    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"
    STATUS = "status"


class Message(BaseModel):
    """
    Message exchanged between agents.

    This model represents a message in the inter-agent communication
    system, containing information about sender, recipient, content,
    and metadata.

    Attributes:
        from_agent: Name of the sending agent.
        to_agent: Name of the receiving agent.
        content: The message content.
        message_type: Type of message.
        timestamp: When the message was created.
        metadata: Optional additional data.

    Example:
        >>> msg = Message(
        ...     from_agent="Orchestrator",
        ...     to_agent="FrontendAgent",
        ...     content="Build the homepage",
        ...     message_type="request"
        ... )
    """

    from_agent: str = Field(..., description="Name of the sending agent")
    to_agent: str = Field(..., description="Name of the receiving agent")
    content: str = Field(..., description="Message content")
    message_type: str = Field(
        default="request",
        description="Type of message (request, response, notification)",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Message timestamp",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "from_agent": "Orchestrator",
                "to_agent": "FrontendAgent",
                "content": "Build the homepage with a hero section",
                "message_type": "request",
                "timestamp": "2024-01-15T10:30:00Z",
            }
        }


class TaskStatus(str, Enum):
    """Status of a task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class Task(BaseModel):
    """
    A task assigned to an agent.

    Represents a unit of work that needs to be completed by an agent,
    including its dependencies and status.

    Attributes:
        id: Unique task identifier.
        description: What needs to be done.
        assigned_to: Agent responsible for this task.
        status: Current task status.
        dependencies: IDs of tasks that must complete first.
        result: Optional result when completed.
        created_at: When the task was created.
        completed_at: When the task was completed.

    Example:
        >>> task = Task(
        ...     id="task-001",
        ...     description="Create navigation component",
        ...     assigned_to="FrontendAgent",
        ...     status="pending"
        ... )
    """

    id: str = Field(default_factory=lambda: str(uuid4()), description="Task ID")
    description: str = Field(..., description="Task description")
    assigned_to: Optional[str] = Field(
        default=None,
        description="Agent assigned to this task",
    )
    status: TaskStatus = Field(
        default=TaskStatus.PENDING,
        description="Current status",
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Task IDs this depends on",
    )
    result: Optional[Any] = Field(
        default=None,
        description="Task result when completed",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp",
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Completion timestamp",
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class ProjectStatus(str, Enum):
    """Status of a project."""

    CREATED = "created"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"


class ProjectCreate(BaseModel):
    """
    Request model for creating a new project.

    Attributes:
        name: Project name.
        requirements: What the client wants built.
    """

    name: str = Field(..., min_length=1, max_length=100, description="Project name")
    requirements: str = Field(
        ...,
        min_length=10,
        description="Project requirements from client",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "name": "My Portfolio Website",
                "requirements": "I need a portfolio website with a hero section, "
                "about me page, project gallery, and contact form.",
            }
        }


class Project(BaseModel):
    """
    A project being developed by the agent team.

    Represents a complete project with its requirements, status,
    and generated files.

    Attributes:
        id: Unique project identifier.
        name: Project name.
        status: Current project status.
        requirements: Original client requirements.
        files: List of generated file paths.
        created_at: When the project was created.
        updated_at: Last update timestamp.

    Example:
        >>> project = Project(
        ...     id="proj-001",
        ...     name="Portfolio Website",
        ...     status="in_progress",
        ...     requirements="Build a portfolio website..."
        ... )
    """

    id: str = Field(default_factory=lambda: str(uuid4()), description="Project ID")
    name: str = Field(..., description="Project name")
    status: ProjectStatus = Field(
        default=ProjectStatus.CREATED,
        description="Project status",
    )
    requirements: str = Field(..., description="Client requirements")
    files: List[str] = Field(
        default_factory=list,
        description="Generated file paths",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp",
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Last update timestamp",
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class AgentStatus(BaseModel):
    """
    Status information for an agent.

    Provides current state information about an agent including
    its operational status and current task.

    Attributes:
        name: Agent name.
        status: Current status (idle, busy, error, offline).
        current_task: Description of current task if busy.

    Example:
        >>> status = AgentStatus(
        ...     name="FrontendAgent",
        ...     status="busy",
        ...     current_task="Building homepage"
        ... )
    """

    name: str = Field(..., description="Agent name")
    status: str = Field(default="idle", description="Agent status")
    current_task: Optional[str] = Field(
        default=None,
        description="Current task being worked on",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "name": "FrontendAgent",
                "status": "busy",
                "current_task": "Building homepage component",
            }
        }


class ChatMessage(BaseModel):
    """
    A chat message between user and agents.

    Represents a single message in the chat conversation,
    either from the user or from the agent system.

    Attributes:
        content: The message content.
        project_id: Associated project ID if any.
        role: Message role (user or assistant).
        timestamp: When the message was sent.

    Example:
        >>> msg = ChatMessage(
        ...     content="Build me a landing page",
        ...     role="user",
        ...     project_id="proj-001"
        ... )
    """

    content: str = Field(..., description="Message content")
    project_id: Optional[str] = Field(
        default=None,
        description="Associated project ID",
    )
    role: str = Field(
        default="user",
        description="Message role (user or assistant)",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Message timestamp",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "content": "I want a landing page with a hero section",
                "project_id": "proj-001",
                "role": "user",
                "timestamp": "2024-01-15T10:30:00Z",
            }
        }


class ChatRequest(BaseModel):
    """
    Request model for sending a chat message.

    Attributes:
        message: The user's message.
        project_id: Optional project to associate with.
    """

    message: str = Field(..., min_length=1, description="User message")
    project_id: Optional[str] = Field(
        default=None,
        description="Project ID to associate with",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "message": "Build me a portfolio website",
                "project_id": None,
            }
        }


class ChatResponse(BaseModel):
    """
    Response model for chat messages.

    Attributes:
        message: The agent's response.
        project_id: Associated project ID if any.
        agent_statuses: Optional status of agents.
    """

    message: str = Field(..., description="Agent response message")
    project_id: Optional[str] = Field(
        default=None,
        description="Associated project ID",
    )
    agent_statuses: Optional[List[AgentStatus]] = Field(
        default=None,
        description="Current agent statuses",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "message": "I'll coordinate the team to build your portfolio website.",
                "project_id": "proj-001",
                "agent_statuses": [
                    {"name": "Planner", "status": "busy", "current_task": "Planning"},
                ],
            }
        }


class FileInfo(BaseModel):
    """
    Information about a project file.

    Attributes:
        name: File name.
        path: Relative path within project.
        type: File or directory.
        size: File size in bytes.
        modified: Last modification time.
    """

    name: str = Field(..., description="File name")
    path: str = Field(..., description="Relative path")
    type: str = Field(..., description="Type (file or directory)")
    size: Optional[int] = Field(default=None, description="Size in bytes")
    modified: Optional[str] = Field(default=None, description="Last modified")


class ErrorResponse(BaseModel):
    """
    Standard error response.

    Attributes:
        detail: Error message.
        code: Optional error code.
    """

    detail: str = Field(..., description="Error message")
    code: Optional[str] = Field(default=None, description="Error code")
