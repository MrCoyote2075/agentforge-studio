"""
AgentForge Studio - Project Memory.

This module implements temporary memory for a single project.
This memory is shared by all agents and clears on new project.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from backend.models.memory import (
    AgentNote,
    ClientPreference,
    Decision,
    ErrorRecord,
    Importance,
    TaskRecord,
)


class ProjectMemory:
    """
    Temporary memory for a single project.
    Shared by all agents. Clears on new project.

    This class stores all project-related context that agents need
    to coordinate and share information during a project's lifecycle.

    Attributes:
        project_id: Unique project identifier.
        _preferences: Dictionary of client preferences.
        _completed_tasks: List of completed tasks.
        _pending_tasks: List of pending tasks.
        _upcoming_tasks: List of upcoming tasks.
        _errors: Dictionary of errors by ID.
        _blockers: List of agent blockers.
        _notes: List of agent notes.
        _decisions: List of decisions made.
    """

    def __init__(self, project_id: str) -> None:
        """
        Initialize project memory.

        Args:
            project_id: Unique project identifier.
        """
        self.project_id = project_id
        self._preferences: dict[str, ClientPreference] = {}
        self._completed_tasks: list[TaskRecord] = []
        self._pending_tasks: list[TaskRecord] = []
        self._upcoming_tasks: list[TaskRecord] = []
        self._errors: dict[str, ErrorRecord] = {}
        self._blockers: list[dict[str, Any]] = []
        self._notes: list[AgentNote] = []
        self._decisions: list[Decision] = []

    # Client context methods

    async def store_client_preference(
        self, key: str, value: Any, importance: str = "normal"
    ) -> None:
        """
        Store something important the client said.

        Args:
            key: Preference key/name.
            value: Preference value.
            importance: Importance level (low, normal, high, critical).
        """
        importance_enum = Importance(importance)
        self._preferences[key] = ClientPreference(
            key=key,
            value=str(value),
            importance=importance_enum,
            recorded_at=datetime.utcnow(),
        )

    async def get_client_preferences(self) -> dict[str, ClientPreference]:
        """
        Get all client preferences.

        Returns:
            Dictionary of client preferences keyed by preference key.
        """
        return self._preferences.copy()

    # Task tracking methods

    async def mark_task_done(self, task_id: str, summary: str) -> None:
        """
        Record completed task.

        Args:
            task_id: Unique task identifier.
            summary: Summary of what was completed.
        """
        # Remove from pending if exists
        self._pending_tasks = [
            t for t in self._pending_tasks if t.task_id != task_id
        ]

        # Add to completed
        self._completed_tasks.append(
            TaskRecord(
                task_id=task_id,
                summary=summary,
                status="done",
                completed_at=datetime.utcnow(),
            )
        )

    async def get_completed_tasks(self) -> list[TaskRecord]:
        """
        Get what's been done.

        Returns:
            List of completed task records.
        """
        return self._completed_tasks.copy()

    async def add_pending_task(self, task: dict[str, Any]) -> None:
        """
        Add task to pending.

        Args:
            task: Task dictionary with at least 'task_id' and 'summary'.
        """
        self._pending_tasks.append(
            TaskRecord(
                task_id=task.get("task_id", str(uuid4())),
                summary=task.get("summary", ""),
                status="pending",
                agent=task.get("agent", ""),
            )
        )

    async def get_pending_tasks(self) -> list[TaskRecord]:
        """
        Get current work.

        Returns:
            List of pending task records.
        """
        return self._pending_tasks.copy()

    async def add_upcoming_task(self, task: dict[str, Any]) -> None:
        """
        Add planned future task.

        Args:
            task: Task dictionary with at least 'task_id' and 'summary'.
        """
        self._upcoming_tasks.append(
            TaskRecord(
                task_id=task.get("task_id", str(uuid4())),
                summary=task.get("summary", ""),
                status="upcoming",
                agent=task.get("agent", ""),
            )
        )

    async def get_upcoming_tasks(self) -> list[TaskRecord]:
        """
        Get what's planned.

        Returns:
            List of upcoming task records.
        """
        return self._upcoming_tasks.copy()

    # Error tracking methods

    async def log_error(
        self, agent: str, error: str, context: dict[str, Any]
    ) -> str:
        """
        Log error that needs fixing.

        Args:
            agent: Agent that encountered the error.
            error: Error description.
            context: Additional context about the error.

        Returns:
            Error ID for future reference.
        """
        error_id = str(uuid4())
        self._errors[error_id] = ErrorRecord(
            id=error_id,
            agent=agent,
            error=error,
            context=context,
            logged_at=datetime.utcnow(),
        )
        return error_id

    async def get_unresolved_errors(self) -> list[ErrorRecord]:
        """
        Get errors that still need fixing.

        Returns:
            List of unresolved error records.
        """
        return [e for e in self._errors.values() if not e.resolved]

    async def mark_error_resolved(self, error_id: str, resolution: str) -> bool:
        """
        Mark error as fixed.

        Args:
            error_id: ID of the error to resolve.
            resolution: Description of how it was resolved.

        Returns:
            True if error was found and resolved, False otherwise.
        """
        if error_id in self._errors:
            self._errors[error_id].resolved = True
            self._errors[error_id].resolution = resolution
            self._errors[error_id].resolved_at = datetime.utcnow()
            return True
        return False

    # Agent coordination methods

    async def log_agent_blocker(
        self, agent: str, blocker: str, blocked_by: str | None = None
    ) -> None:
        """
        Log when agent is blocked by something.

        Args:
            agent: Agent that is blocked.
            blocker: Description of what's blocking.
            blocked_by: Agent or resource that's causing the block.
        """
        self._blockers.append({
            "agent": agent,
            "blocker": blocker,
            "blocked_by": blocked_by,
            "logged_at": datetime.utcnow().isoformat(),
        })

    async def add_agent_note(self, agent: str, note: str) -> None:
        """
        Agent leaves note for other agents.

        Args:
            agent: Agent leaving the note.
            note: Note content.
        """
        self._notes.append(
            AgentNote(
                from_agent=agent,
                to_agent=None,  # For all agents
                note=note,
            )
        )

    async def add_targeted_note(
        self, from_agent: str, to_agent: str, note: str
    ) -> None:
        """
        Agent leaves note for a specific agent.

        Args:
            from_agent: Agent leaving the note.
            to_agent: Target agent.
            note: Note content.
        """
        self._notes.append(
            AgentNote(
                from_agent=from_agent,
                to_agent=to_agent,
                note=note,
            )
        )

    async def get_agent_notes(self, for_agent: str | None = None) -> list[AgentNote]:
        """
        Get notes (optionally filtered by recipient).

        Args:
            for_agent: If specified, get notes for this agent.

        Returns:
            List of agent notes.
        """
        if for_agent is None:
            return self._notes.copy()
        return [
            n
            for n in self._notes
            if n.to_agent is None or n.to_agent == for_agent
        ]

    # Decision methods

    async def record_decision(
        self, decision: str, reason: str, made_by: str
    ) -> None:
        """
        Record important decision.

        Args:
            decision: The decision made.
            reason: Reason for the decision.
            made_by: Who made the decision.
        """
        self._decisions.append(
            Decision(
                decision=decision,
                reason=reason,
                made_by=made_by,
            )
        )

    async def get_decisions(self) -> list[Decision]:
        """
        Get all decisions made.

        Returns:
            List of decisions.
        """
        return self._decisions.copy()

    # Full context for agent

    async def get_context_for_agent(self, agent_name: str) -> dict[str, Any]:
        """
        Build complete context for an agent to work.
        Includes: preferences, done, pending, upcoming, errors, notes, decisions.

        Args:
            agent_name: Name of the agent requesting context.

        Returns:
            Dictionary containing all context for the agent.
        """
        return {
            "project_id": self.project_id,
            "agent_name": agent_name,
            "preferences": list(self._preferences.values()),
            "completed_tasks": self._completed_tasks,
            "pending_tasks": self._pending_tasks,
            "upcoming_tasks": self._upcoming_tasks,
            "unresolved_errors": await self.get_unresolved_errors(),
            "blockers": self._blockers,
            "notes": await self.get_agent_notes(for_agent=agent_name),
            "decisions": self._decisions,
        }

    # Lifecycle methods

    async def clear(self) -> None:
        """Clear all memory (called on new project)."""
        self._preferences.clear()
        self._completed_tasks.clear()
        self._pending_tasks.clear()
        self._upcoming_tasks.clear()
        self._errors.clear()
        self._blockers.clear()
        self._notes.clear()
        self._decisions.clear()
