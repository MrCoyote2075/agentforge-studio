"""
AgentForge Studio - Message Models.

This module defines Pydantic models for inter-agent communication,
including messages, tasks, events, and status updates.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Types of messages exchanged between agents."""

    TASK = "TASK"
    RESULT = "RESULT"
    ERROR = "ERROR"
    STATUS = "STATUS"
    QUERY = "QUERY"
    RESPONSE = "RESPONSE"


class TaskPriority(str, Enum):
    """Priority levels for tasks."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TaskState(str, Enum):
    """States of a task."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class AgentStatusType(str, Enum):
    """Status types for agents."""

    IDLE = "IDLE"
    BUSY = "BUSY"
    WAITING = "WAITING"
    ERROR = "ERROR"
    OFFLINE = "OFFLINE"


class EventType(str, Enum):
    """Types of events in the system."""

    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    FILE_CREATED = "file_created"
    FILE_UPDATED = "file_updated"
    ERROR_OCCURRED = "error_occurred"
    MILESTONE_REACHED = "milestone_reached"
    PREVIEW_READY = "preview_ready"


class Message(BaseModel):
    """
    Base message model for inter-agent communication.

    Attributes:
        id: Unique message identifier.
        from_agent: Name of the sending agent.
        to_agent: Name of the receiving agent (can be None for broadcasts).
        type: Type of message.
        payload: Message content/data.
        timestamp: When the message was created.
        priority: Message priority level.
    """

    id: str = Field(default_factory=lambda: str(uuid4()), description="Message ID")
    from_agent: str = Field(..., description="Name of the sending agent")
    to_agent: str | None = Field(
        default=None, description="Name of the receiving agent"
    )
    type: MessageType = Field(..., description="Type of message")
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Message content/data"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Message timestamp"
    )
    priority: TaskPriority = Field(
        default=TaskPriority.MEDIUM, description="Message priority"
    )

    model_config = {
        "use_enum_values": True,
        "json_schema_extra": {
            "example": {
                "id": "msg-001",
                "from_agent": "planner",
                "to_agent": "frontend_agent",
                "type": "TASK",
                "payload": {"action": "create_html", "page": "home"},
                "priority": "MEDIUM",
            }
        },
    }


class TaskMessage(Message):
    """
    Message for task assignments.

    Attributes:
        task_id: ID of the task being assigned.
        task_description: Description of the task.
        dependencies: List of task IDs this task depends on.
        timeout: Optional timeout in seconds for the task.
    """

    task_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Task ID"
    )
    task_description: str = Field(..., description="Description of the task")
    dependencies: list[str] = Field(
        default_factory=list, description="Task IDs this depends on"
    )
    timeout: float | None = Field(
        default=None, description="Task timeout in seconds"
    )

    def __init__(self, **data: Any) -> None:
        if "type" not in data:
            data["type"] = MessageType.TASK
        super().__init__(**data)


class ResultMessage(Message):
    """
    Message for task results.

    Attributes:
        task_id: ID of the completed task.
        success: Whether the task succeeded.
        result: The task result data.
        error: Error message if task failed.
        execution_time: Time taken to execute the task in seconds.
    """

    task_id: str = Field(..., description="ID of the completed task")
    success: bool = Field(default=True, description="Whether the task succeeded")
    result: Any = Field(default=None, description="Task result data")
    error: str | None = Field(default=None, description="Error message if failed")
    execution_time: float | None = Field(
        default=None, description="Execution time in seconds"
    )

    def __init__(self, **data: Any) -> None:
        if "type" not in data:
            data["type"] = MessageType.RESULT
        super().__init__(**data)


class StatusMessage(Message):
    """
    Message for agent status updates.

    Attributes:
        agent_name: Name of the agent reporting status.
        status: Current agent status.
        current_task: Description of current task if busy.
        progress: Progress percentage (0-100).
    """

    agent_name: str = Field(..., description="Name of the agent")
    status: AgentStatusType = Field(..., description="Current agent status")
    current_task: str | None = Field(
        default=None, description="Current task description"
    )
    progress: float | None = Field(
        default=None, description="Progress percentage (0-100)"
    )

    def __init__(self, **data: Any) -> None:
        if "type" not in data:
            data["type"] = MessageType.STATUS
        super().__init__(**data)


class ErrorMessage(Message):
    """
    Message for error reporting.

    Attributes:
        error_code: Error code for classification.
        error_message: Human-readable error message.
        stack_trace: Optional stack trace.
        recoverable: Whether the error is recoverable.
        context: Additional context about the error.
    """

    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Error message")
    stack_trace: str | None = Field(default=None, description="Stack trace")
    recoverable: bool = Field(
        default=False, description="Whether the error is recoverable"
    )
    context: dict[str, Any] = Field(
        default_factory=dict, description="Additional error context"
    )

    def __init__(self, **data: Any) -> None:
        if "type" not in data:
            data["type"] = MessageType.ERROR
        super().__init__(**data)


class Event(BaseModel):
    """
    Model for system events.

    Attributes:
        id: Unique event identifier.
        type: Type of event.
        source: Source of the event (agent or system).
        data: Event data/payload.
        timestamp: When the event occurred.
    """

    id: str = Field(default_factory=lambda: str(uuid4()), description="Event ID")
    type: EventType = Field(..., description="Type of event")
    source: str = Field(..., description="Source of the event")
    data: dict[str, Any] = Field(
        default_factory=dict, description="Event data/payload"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Event timestamp"
    )

    model_config = {
        "use_enum_values": True,
        "json_schema_extra": {
            "example": {
                "id": "evt-001",
                "type": "file_created",
                "source": "frontend_agent",
                "data": {"path": "index.html", "size": 1024},
            }
        },
    }


class Task(BaseModel):
    """
    Full task model with all details.

    Attributes:
        id: Unique task identifier.
        type: Type of task (e.g., create_html, create_css).
        description: Task description.
        agent: Agent assigned to this task.
        state: Current task state.
        priority: Task priority level.
        dependencies: List of task IDs this task depends on.
        payload: Task-specific data.
        result: Task result when completed.
        error: Error message if task failed.
        created_at: When the task was created.
        started_at: When the task was started.
        completed_at: When the task was completed.
        timeout: Task timeout in seconds.
    """

    id: str = Field(default_factory=lambda: str(uuid4()), description="Task ID")
    type: str = Field(..., description="Type of task")
    description: str = Field(..., description="Task description")
    agent: str | None = Field(default=None, description="Agent assigned to this task")
    state: TaskState = Field(default=TaskState.PENDING, description="Current state")
    priority: TaskPriority = Field(
        default=TaskPriority.MEDIUM, description="Task priority"
    )
    dependencies: list[str] = Field(
        default_factory=list, description="Task IDs this depends on"
    )
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Task-specific data"
    )
    result: Any = Field(default=None, description="Task result")
    error: str | None = Field(default=None, description="Error message if failed")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    started_at: datetime | None = Field(
        default=None, description="Start timestamp"
    )
    completed_at: datetime | None = Field(
        default=None, description="Completion timestamp"
    )
    timeout: float | None = Field(
        default=None, description="Task timeout in seconds"
    )

    model_config = {
        "use_enum_values": True,
        "json_schema_extra": {
            "example": {
                "id": "task-001",
                "type": "create_html",
                "description": "Create the homepage HTML",
                "agent": "frontend_agent",
                "state": "PENDING",
                "priority": "HIGH",
                "dependencies": [],
            }
        },
    }


class AgentInfo(BaseModel):
    """
    Information about a registered agent.

    Attributes:
        name: Agent name.
        status: Current agent status.
        capabilities: List of capabilities (file types, task types).
        current_task_id: ID of current task if busy.
        last_heartbeat: Last heartbeat timestamp.
        registered_at: When the agent was registered.
    """

    name: str = Field(..., description="Agent name")
    status: AgentStatusType = Field(
        default=AgentStatusType.IDLE, description="Current status"
    )
    capabilities: list[str] = Field(
        default_factory=list, description="Agent capabilities"
    )
    current_task_id: str | None = Field(
        default=None, description="Current task ID"
    )
    last_heartbeat: datetime = Field(
        default_factory=datetime.utcnow, description="Last heartbeat"
    )
    registered_at: datetime = Field(
        default_factory=datetime.utcnow, description="Registration time"
    )

    model_config = {
        "use_enum_values": True,
        "json_schema_extra": {
            "example": {
                "name": "frontend_agent",
                "status": "IDLE",
                "capabilities": ["html", "css", "js"],
            }
        },
    }
