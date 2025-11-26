"""
AgentForge Studio - Memory Models.

This module defines Pydantic models for the memory system,
including project memory and application memory entities.
"""

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class Importance(str, Enum):
    """Importance levels for client preferences."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class ClientPreference(BaseModel):
    """
    Model for storing client preferences.

    Attributes:
        key: Preference key/name.
        value: Preference value.
        importance: Importance level.
        recorded_at: When the preference was recorded.
    """

    key: str = Field(..., description="Preference key/name")
    value: str = Field(..., description="Preference value")
    importance: Importance = Field(
        default=Importance.NORMAL, description="Importance level"
    )
    recorded_at: datetime = Field(
        default_factory=datetime.utcnow, description="When recorded"
    )

    model_config = {"use_enum_values": True}


class TaskRecord(BaseModel):
    """
    Model for tracking tasks.

    Attributes:
        task_id: Unique task identifier.
        summary: Task summary/description.
        status: Task status (done, pending, upcoming).
        agent: Agent responsible for the task.
        recorded_at: When the task was recorded.
        completed_at: When the task was completed (if done).
    """

    task_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Task ID"
    )
    summary: str = Field(..., description="Task summary")
    status: str = Field(..., description="Task status (done, pending, upcoming)")
    agent: str = Field(default="", description="Agent responsible")
    recorded_at: datetime = Field(
        default_factory=datetime.utcnow, description="When recorded"
    )
    completed_at: datetime | None = Field(
        default=None, description="When completed"
    )


class ErrorRecord(BaseModel):
    """
    Model for tracking errors.

    Attributes:
        id: Unique error identifier.
        agent: Agent that encountered the error.
        error: Error description.
        context: Additional context about the error.
        resolved: Whether the error has been resolved.
        resolution: How the error was resolved.
        logged_at: When the error was logged.
        resolved_at: When the error was resolved.
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()), description="Error ID"
    )
    agent: str = Field(..., description="Agent that encountered the error")
    error: str = Field(..., description="Error description")
    context: dict = Field(default_factory=dict, description="Additional context")
    resolved: bool = Field(default=False, description="Whether resolved")
    resolution: str | None = Field(default=None, description="Resolution description")
    logged_at: datetime = Field(
        default_factory=datetime.utcnow, description="When logged"
    )
    resolved_at: datetime | None = Field(
        default=None, description="When resolved"
    )


class AgentNote(BaseModel):
    """
    Model for agent notes.

    Attributes:
        id: Unique note identifier.
        from_agent: Agent that created the note.
        to_agent: Target agent (None = for all agents).
        note: The note content.
        created_at: When the note was created.
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()), description="Note ID"
    )
    from_agent: str = Field(..., description="Agent that created the note")
    to_agent: str | None = Field(
        default=None, description="Target agent (None = for all)"
    )
    note: str = Field(..., description="Note content")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When created"
    )


class Decision(BaseModel):
    """
    Model for recording decisions.

    Attributes:
        id: Unique decision identifier.
        decision: The decision made.
        reason: Reason for the decision.
        made_by: Who made the decision.
        created_at: When the decision was made.
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()), description="Decision ID"
    )
    decision: str = Field(..., description="The decision made")
    reason: str = Field(..., description="Reason for the decision")
    made_by: str = Field(..., description="Who made the decision")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When made"
    )


class Pattern(BaseModel):
    """
    Model for storing code patterns.

    Attributes:
        id: Unique pattern identifier.
        name: Pattern name.
        description: Pattern description.
        code_example: Example code for the pattern.
        category: Pattern category.
        times_used: Number of times the pattern was used.
        created_at: When the pattern was created.
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()), description="Pattern ID"
    )
    name: str = Field(..., description="Pattern name")
    description: str = Field(default="", description="Pattern description")
    code_example: str = Field(default="", description="Example code")
    category: str = Field(default="", description="Pattern category")
    times_used: int = Field(default=0, description="Times used")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When created"
    )


class BestPractice(BaseModel):
    """
    Model for storing best practices.

    Attributes:
        id: Unique best practice identifier.
        practice: The best practice.
        context: Context where the practice applies.
        learned_from: Source of the practice (project_id or "manual").
        created_at: When the practice was recorded.
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()), description="Best practice ID"
    )
    practice: str = Field(..., description="The best practice")
    context: str = Field(default="", description="Context where it applies")
    learned_from: str = Field(
        default="manual", description="Source (project_id or 'manual')"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When created"
    )


class MistakeRecord(BaseModel):
    """
    Model for storing mistakes to avoid.

    Attributes:
        id: Unique mistake identifier.
        mistake: Description of the mistake.
        consequence: What happens if the mistake is made.
        how_to_avoid: How to avoid the mistake.
        agent: Agent type this applies to.
        occurrences: Number of times this mistake was made.
        created_at: When the mistake was recorded.
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()), description="Mistake ID"
    )
    mistake: str = Field(..., description="Description of the mistake")
    consequence: str = Field(default="", description="Consequence of the mistake")
    how_to_avoid: str = Field(default="", description="How to avoid")
    agent: str = Field(default="", description="Agent type this applies to")
    occurrences: int = Field(default=1, description="Number of occurrences")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When created"
    )


class AgentContext(BaseModel):
    """
    Complete context for an agent.

    This model combines project memory and application memory
    to provide all context an agent needs for its work.

    Attributes:
        project_id: Project identifier.
        agent_name: Name of the agent.
        client_preferences: List of client preferences.
        completed_tasks: List of completed tasks.
        pending_tasks: List of pending tasks.
        upcoming_tasks: List of upcoming tasks.
        unresolved_errors: List of unresolved errors.
        agent_notes: List of agent notes.
        decisions: List of decisions made.
        relevant_patterns: List of relevant patterns.
        best_practices: List of best practices.
        mistakes_to_avoid: List of mistakes to avoid.
        formatted_context: Formatted context string for prompts.
    """

    project_id: str = Field(..., description="Project identifier")
    agent_name: str = Field(..., description="Agent name")

    # From project memory
    client_preferences: list[ClientPreference] = Field(
        default_factory=list, description="Client preferences"
    )
    completed_tasks: list[TaskRecord] = Field(
        default_factory=list, description="Completed tasks"
    )
    pending_tasks: list[TaskRecord] = Field(
        default_factory=list, description="Pending tasks"
    )
    upcoming_tasks: list[TaskRecord] = Field(
        default_factory=list, description="Upcoming tasks"
    )
    unresolved_errors: list[ErrorRecord] = Field(
        default_factory=list, description="Unresolved errors"
    )
    agent_notes: list[AgentNote] = Field(
        default_factory=list, description="Agent notes"
    )
    decisions: list[Decision] = Field(
        default_factory=list, description="Decisions made"
    )

    # From app memory
    relevant_patterns: list[Pattern] = Field(
        default_factory=list, description="Relevant patterns"
    )
    best_practices: list[BestPractice] = Field(
        default_factory=list, description="Best practices"
    )
    mistakes_to_avoid: list[MistakeRecord] = Field(
        default_factory=list, description="Mistakes to avoid"
    )

    # Formatted for prompt
    formatted_context: str = Field(
        default="", description="Formatted context string"
    )
