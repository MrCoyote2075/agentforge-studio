"""
AgentForge Studio - Memory Manager.

This module implements the central manager that coordinates all
memory operations and provides a unified interface for agents.
"""

import logging
from typing import Any

from backend.core.memory.application_memory import ApplicationMemory
from backend.core.memory.project_memory import ProjectMemory
from backend.models.memory import AgentContext


class MemoryManager:
    """
    Central manager that coordinates all memory operations.
    Provides unified interface for agents.

    This class acts as the single point of access for all memory
    operations, managing both temporary project memory and
    permanent application memory.

    Attributes:
        project_memories: Dictionary of project memories by project ID.
        app_memory: Application memory instance.
        logger: Logger instance.
    """

    def __init__(self, db_path: str = "./data/app_memory.db") -> None:
        """
        Initialize memory manager.

        Args:
            db_path: Path to the SQLite database for application memory.
        """
        self.project_memories: dict[str, ProjectMemory] = {}
        self.app_memory = ApplicationMemory(db_path)
        self.logger = logging.getLogger("memory_manager")
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize memory systems."""
        await self.app_memory.initialize()
        self._initialized = True
        self.logger.info("Memory manager initialized")

    # Project memory management

    def get_project_memory(self, project_id: str) -> ProjectMemory:
        """
        Get or create project memory.

        Args:
            project_id: Project identifier.

        Returns:
            ProjectMemory instance for the project.
        """
        if project_id not in self.project_memories:
            self.project_memories[project_id] = ProjectMemory(project_id)
            self.logger.debug(f"Created project memory for {project_id}")
        return self.project_memories[project_id]

    async def clear_project_memory(self, project_id: str) -> None:
        """
        Clear project memory (on new project).

        Args:
            project_id: Project identifier to clear.
        """
        if project_id in self.project_memories:
            await self.project_memories[project_id].clear()
            del self.project_memories[project_id]
            self.logger.info(f"Cleared project memory for {project_id}")

    def has_project_memory(self, project_id: str) -> bool:
        """
        Check if project memory exists.

        Args:
            project_id: Project identifier.

        Returns:
            True if project memory exists.
        """
        return project_id in self.project_memories

    # Unified context building

    async def build_agent_context(
        self, project_id: str, agent_name: str
    ) -> AgentContext:
        """
        Build complete context for agent including:
        - Project memory (preferences, tasks, errors, notes)
        - Relevant application learnings
        - Agent-specific best practices
        - Mistakes to avoid

        Args:
            project_id: Project identifier.
            agent_name: Name of the agent.

        Returns:
            AgentContext with all relevant context.
        """
        project_mem = self.get_project_memory(project_id)

        # Get project context
        project_context = await project_mem.get_context_for_agent(agent_name)

        # Get application learnings
        app_patterns = await self.app_memory.get_patterns()
        app_practices = await self.app_memory.get_best_practices()
        app_mistakes = await self.app_memory.get_mistakes_for_agent(agent_name)

        # Build formatted context string
        formatted = await self._format_context(
            project_context, app_patterns[:5], app_practices[:5], app_mistakes[:5]
        )

        return AgentContext(
            project_id=project_id,
            agent_name=agent_name,
            client_preferences=list(project_context["preferences"]),
            completed_tasks=project_context["completed_tasks"],
            pending_tasks=project_context["pending_tasks"],
            upcoming_tasks=project_context["upcoming_tasks"],
            unresolved_errors=project_context["unresolved_errors"],
            agent_notes=project_context["notes"],
            decisions=project_context["decisions"],
            relevant_patterns=app_patterns[:5],
            best_practices=app_practices[:5],
            mistakes_to_avoid=app_mistakes[:5],
            formatted_context=formatted,
        )

    async def _format_context(
        self,
        project_context: dict[str, Any],
        patterns: list,
        practices: list,
        mistakes: list,
    ) -> str:
        """
        Format context into a string suitable for AI prompts.

        Args:
            project_context: Dictionary of project context.
            patterns: List of relevant patterns.
            practices: List of best practices.
            mistakes: List of mistakes to avoid.

        Returns:
            Formatted context string.
        """
        lines = []

        # Project Context
        lines.append("## Project Context")

        # Client preferences
        preferences = project_context.get("preferences", [])
        if preferences:
            lines.append("\n### Client Preferences")
            for pref in preferences:
                importance = (
                    f" [{pref.importance}]" if pref.importance != "normal" else ""
                )
                lines.append(f"- {pref.key}: {pref.value}{importance}")

        # Completed tasks
        completed = project_context.get("completed_tasks", [])
        if completed:
            lines.append("\n### Completed")
            for task in completed[-5:]:  # Last 5 completed
                lines.append(f"- {task.summary}")

        # Pending tasks
        pending = project_context.get("pending_tasks", [])
        if pending:
            lines.append("\n### Current Work")
            for task in pending:
                lines.append(f"- {task.summary}")

        # Upcoming tasks
        upcoming = project_context.get("upcoming_tasks", [])
        if upcoming:
            lines.append("\n### Upcoming")
            for task in upcoming[:5]:  # Next 5 upcoming
                lines.append(f"- {task.summary}")

        # Unresolved errors
        errors = project_context.get("unresolved_errors", [])
        if errors:
            lines.append("\n### Issues to Address")
            for error in errors:
                lines.append(f"- {error.error} (reported by {error.agent})")

        # Agent notes
        notes = project_context.get("notes", [])
        if notes:
            lines.append("\n### Notes from Team")
            for note in notes[-5:]:  # Last 5 notes
                lines.append(f"- {note.from_agent}: {note.note}")

        # Decisions
        decisions = project_context.get("decisions", [])
        if decisions:
            lines.append("\n### Key Decisions")
            for decision in decisions[-5:]:  # Last 5 decisions
                lines.append(f"- {decision.decision} (by {decision.made_by})")

        # Application learnings
        if practices:
            lines.append("\n## Best Practices (from past projects)")
            for practice in practices:
                lines.append(f"- {practice.practice}")

        if mistakes:
            lines.append("\n## Avoid These Mistakes")
            for mistake in mistakes:
                lines.append(f"- {mistake.mistake}")
                if mistake.how_to_avoid:
                    lines.append(f"  → Instead: {mistake.how_to_avoid}")

        return "\n".join(lines)

    # Learning

    async def extract_learnings(
        self, project_id: str, feedback: str | None = None
    ) -> None:
        """
        Called when project completes.
        Extracts learnings and stores in app memory.

        Args:
            project_id: Project identifier.
            feedback: Optional feedback from client.
        """
        if feedback:
            # Store the feedback for future processing
            await self.app_memory.learn_from_feedback(
                project_id=project_id,
                feedback=feedback,
                rating=0,  # Will be updated later if rating provided
            )
            self.logger.info(f"Stored feedback from project {project_id}")

        # Get project memory for analysis
        if project_id in self.project_memories:
            project_mem = self.project_memories[project_id]

            # Extract successful patterns from decisions
            decisions = await project_mem.get_decisions()
            for decision in decisions:
                # Store significant decisions as potential patterns
                if len(decision.decision) > 20:  # Meaningful decision
                    await self.app_memory.store_best_practice(
                        practice=decision.decision,
                        context=decision.reason,
                        learned_from=project_id,
                    )

            self.logger.info(f"Extracted learnings from project {project_id}")

    # Convenience methods for quick access

    async def store_preference(
        self,
        project_id: str,
        key: str,
        value: Any,
        importance: str = "normal",
    ) -> None:
        """
        Store client preference for a project.

        Args:
            project_id: Project identifier.
            key: Preference key.
            value: Preference value.
            importance: Importance level.
        """
        project_mem = self.get_project_memory(project_id)
        await project_mem.store_client_preference(key, value, importance)

    async def log_error(
        self,
        project_id: str,
        agent: str,
        error: str,
        context: dict[str, Any],
    ) -> str:
        """
        Log an error for a project.

        Args:
            project_id: Project identifier.
            agent: Agent that encountered the error.
            error: Error description.
            context: Additional context.

        Returns:
            Error ID.
        """
        project_mem = self.get_project_memory(project_id)
        return await project_mem.log_error(agent, error, context)

    async def add_note(
        self,
        project_id: str,
        from_agent: str,
        note: str,
        to_agent: str | None = None,
    ) -> None:
        """
        Add an agent note for a project.

        Args:
            project_id: Project identifier.
            from_agent: Agent leaving the note.
            note: Note content.
            to_agent: Target agent (None for all).
        """
        project_mem = self.get_project_memory(project_id)
        if to_agent:
            await project_mem.add_targeted_note(from_agent, to_agent, note)
        else:
            await project_mem.add_agent_note(from_agent, note)

    async def record_decision(
        self,
        project_id: str,
        decision: str,
        reason: str,
        made_by: str,
    ) -> None:
        """
        Record a decision for a project.

        Args:
            project_id: Project identifier.
            decision: The decision made.
            reason: Reason for the decision.
            made_by: Who made the decision.
        """
        project_mem = self.get_project_memory(project_id)
        await project_mem.record_decision(decision, reason, made_by)

    async def get_formatted_context(
        self, project_id: str, agent_name: str
    ) -> str:
        """
        Get formatted context string for an agent.

        Args:
            project_id: Project identifier.
            agent_name: Agent name.

        Returns:
            Formatted context string ready for prompts.
        """
        context = await self.build_agent_context(project_id, agent_name)
        return context.formatted_context

    async def close(self) -> None:
        """Clean up resources."""
        await self.app_memory.close()
        self.logger.info("Memory manager closed")
