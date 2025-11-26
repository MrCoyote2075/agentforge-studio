"""
AgentForge Studio - Context Builder.

This module builds formatted context strings for AI prompts.
Combines memories into useful context for agents.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.core.memory.memory_manager import MemoryManager


class ContextBuilder:
    """
    Builds formatted context strings for AI prompts.
    Combines memories into useful context for agents.

    This class provides various formatting options for building
    context strings that can be injected into AI agent prompts.

    Attributes:
        memory_manager: The memory manager instance.
    """

    def __init__(self, memory_manager: "MemoryManager") -> None:
        """
        Initialize context builder.

        Args:
            memory_manager: The memory manager instance.
        """
        self.memory_manager = memory_manager

    async def build_context(self, project_id: str, agent_name: str) -> str:
        """
        Build a formatted context string for agent prompts.

        Returns a comprehensive context including project status,
        client preferences, task tracking, errors, notes, and
        learnings from past projects.

        Args:
            project_id: Project identifier.
            agent_name: Name of the agent.

        Returns:
            Formatted context string ready for use in prompts.
        """
        context = await self.memory_manager.build_agent_context(
            project_id, agent_name
        )
        return context.formatted_context

    async def build_minimal_context(
        self, project_id: str, agent_name: str
    ) -> str:
        """
        Build a minimal context string with only essential info.

        Args:
            project_id: Project identifier.
            agent_name: Name of the agent.

        Returns:
            Minimal context string.
        """
        context = await self.memory_manager.build_agent_context(
            project_id, agent_name
        )

        lines = [f"## Context for {agent_name}"]

        # Only include preferences
        if context.client_preferences:
            for pref in context.client_preferences[:3]:
                lines.append(f"- {pref.key}: {pref.value}")

        # Only include pending tasks
        if context.pending_tasks:
            lines.append("\n### Current Tasks")
            for task in context.pending_tasks[:3]:
                lines.append(f"- {task.summary}")

        # Only include critical errors
        critical_errors = [
            e for e in context.unresolved_errors
            if "critical" in e.error.lower() or "urgent" in e.error.lower()
        ]
        if critical_errors:
            lines.append("\n### Critical Issues")
            for error in critical_errors[:2]:
                lines.append(f"- {error.error}")

        return "\n".join(lines)

    async def build_task_focused_context(
        self, project_id: str, agent_name: str, task_type: str
    ) -> str:
        """
        Build context focused on a specific task type.

        Args:
            project_id: Project identifier.
            agent_name: Name of the agent.
            task_type: Type of task (e.g., "html", "css", "review").

        Returns:
            Task-focused context string.
        """
        # Get project context
        context = await self.memory_manager.build_agent_context(
            project_id, agent_name
        )

        # Get task-specific learnings
        learnings = await self.memory_manager.app_memory.get_learnings_for_task(
            task_type
        )

        lines = [f"## {task_type.upper()} Task Context"]

        # Client preferences related to task
        if context.client_preferences:
            lines.append("\n### Client Wants")
            for pref in context.client_preferences:
                if (
                    task_type.lower() in pref.key.lower()
                    or task_type.lower() in pref.value.lower()
                ):
                    lines.append(f"- {pref.key}: {pref.value}")

        # Relevant patterns
        patterns = learnings.get("patterns", [])
        if patterns:
            lines.append(f"\n### {task_type.upper()} Patterns to Use")
            for pattern in patterns[:3]:
                lines.append(f"- {pattern.name}: {pattern.description}")

        # Best practices
        practices = learnings.get("best_practices", [])
        if practices:
            lines.append(f"\n### Best Practices for {task_type.upper()}")
            for practice in practices[:3]:
                lines.append(f"- {practice.practice}")

        # Mistakes to avoid
        mistakes = learnings.get("mistakes_to_avoid", [])
        if mistakes:
            lines.append(f"\n### Avoid These {task_type.upper()} Mistakes")
            for mistake in mistakes[:3]:
                lines.append(f"- {mistake.mistake}")

        return "\n".join(lines)

    async def build_review_context(self, project_id: str) -> str:
        """
        Build context for code review.

        Args:
            project_id: Project identifier.

        Returns:
            Review-focused context string.
        """
        context = await self.memory_manager.build_agent_context(
            project_id, "Reviewer"
        )

        lines = ["## Code Review Context"]

        # What was built
        if context.completed_tasks:
            lines.append("\n### What Was Built")
            for task in context.completed_tasks[-10:]:
                lines.append(f"- {task.summary}")

        # Client requirements
        if context.client_preferences:
            lines.append("\n### Requirements to Verify")
            for pref in context.client_preferences:
                lines.append(f"- {pref.key}: {pref.value}")

        # Decisions made
        if context.decisions:
            lines.append("\n### Decisions to Consider")
            for decision in context.decisions[-5:]:
                lines.append(f"- {decision.decision}")

        # Common mistakes for reviewing
        if context.mistakes_to_avoid:
            lines.append("\n### Check For These Issues")
            for mistake in context.mistakes_to_avoid[:5]:
                lines.append(f"- {mistake.mistake}")

        return "\n".join(lines)

    async def build_handoff_context(
        self,
        project_id: str,
        from_agent: str,
        to_agent: str,
    ) -> str:
        """
        Build context for handoff between agents.

        Args:
            project_id: Project identifier.
            from_agent: Agent handing off.
            to_agent: Agent receiving.

        Returns:
            Handoff context string.
        """
        project_mem = self.memory_manager.get_project_memory(project_id)

        lines = [f"## Handoff from {from_agent} to {to_agent}"]

        # Get notes from the handing-off agent
        notes = await project_mem.get_agent_notes(for_agent=to_agent)
        from_agent_notes = [n for n in notes if n.from_agent == from_agent]

        if from_agent_notes:
            lines.append(f"\n### Notes from {from_agent}")
            for note in from_agent_notes[-5:]:
                lines.append(f"- {note.note}")

        # What was completed
        completed = await project_mem.get_completed_tasks()
        if completed:
            lines.append("\n### Already Done")
            for task in completed[-5:]:
                lines.append(f"- {task.summary}")

        # What's pending
        pending = await project_mem.get_pending_tasks()
        if pending:
            lines.append("\n### Your Tasks")
            for task in pending[:5]:
                lines.append(f"- {task.summary}")

        # Any blockers
        errors = await project_mem.get_unresolved_errors()
        if errors:
            lines.append("\n### Watch Out For")
            for error in errors[:3]:
                lines.append(f"- {error.error}")

        return "\n".join(lines)
