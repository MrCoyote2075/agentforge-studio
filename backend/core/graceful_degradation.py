"""
AgentForge Studio - Graceful Degradation.

This module implements graceful degradation handling for partial
failures, allowing the system to continue with reduced functionality.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any


class DegradationLevel(str, Enum):
    """Levels of degradation severity."""

    NONE = "none"  # No degradation
    MINOR = "minor"  # Minor functionality affected
    MODERATE = "moderate"  # Some features unavailable
    SEVERE = "severe"  # Significant functionality lost
    CRITICAL = "critical"  # Core functionality affected


class DegradationAction(str, Enum):
    """Actions taken during degradation."""

    SWITCHED_BACKUP = "switched_backup"
    SKIPPED_TASK = "skipped_task"
    USED_FALLBACK = "used_fallback"
    REDUCED_QUALITY = "reduced_quality"
    CONTINUED_WITH_WARNING = "continued_with_warning"
    FAILED = "failed"


class DegradationEvent:
    """Record of a degradation event."""

    def __init__(
        self,
        component: str,
        action: DegradationAction,
        level: DegradationLevel,
        message: str,
        original_error: str | None = None,
    ) -> None:
        """
        Initialize DegradationEvent.

        Args:
            component: The component that degraded.
            action: The action taken.
            level: Severity level.
            message: Description of the degradation.
            original_error: The original error if applicable.
        """
        self.component = component
        self.action = action
        self.level = level
        self.message = message
        self.original_error = original_error
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "component": self.component,
            "action": self.action.value,
            "level": self.level.value,
            "message": self.message,
            "original_error": self.original_error,
            "timestamp": self.timestamp.isoformat(),
        }


class GracefulDegradation:
    """
    Handles graceful degradation when components fail.

    Provides fallback mechanisms and continues operation with
    reduced functionality when possible.

    Attributes:
        backup_agents: Mapping of agent -> backup agent.
        backup_providers: Mapping of API provider -> backup provider.
        critical_agents: Set of agents that cannot be skipped.
        events: List of degradation events.
        logger: Logger instance.

    Example:
        >>> degradation = GracefulDegradation()
        >>> degradation.register_backup_agent("FrontendAgent", "HelperAgent")
        >>> action = await degradation.on_agent_failure("FrontendAgent", error)
    """

    def __init__(self) -> None:
        """Initialize GracefulDegradation."""
        self._backup_agents: dict[str, str] = {}
        self._backup_providers: dict[str, str] = {}
        self._critical_agents: set[str] = {"Orchestrator", "Intermediator"}
        self._events: list[DegradationEvent] = []
        self._current_level = DegradationLevel.NONE
        self._active_degradations: dict[str, DegradationEvent] = {}
        self.logger = logging.getLogger("graceful_degradation")

    def register_backup_agent(self, primary: str, backup: str) -> None:
        """
        Register a backup agent for a primary agent.

        Args:
            primary: The primary agent name.
            backup: The backup agent name.
        """
        self._backup_agents[primary] = backup
        self.logger.info(f"Registered {backup} as backup for {primary}")

    def register_backup_provider(self, primary: str, backup: str) -> None:
        """
        Register a backup API provider.

        Args:
            primary: The primary provider name.
            backup: The backup provider name.
        """
        self._backup_providers[primary] = backup
        self.logger.info(f"Registered {backup} as backup for provider {primary}")

    def set_critical_agents(self, agents: set[str]) -> None:
        """
        Set which agents are critical (cannot be skipped).

        Args:
            agents: Set of critical agent names.
        """
        self._critical_agents = agents
        self.logger.info(f"Set critical agents: {agents}")

    async def on_agent_failure(
        self,
        agent_name: str,
        error: Exception,
    ) -> str:
        """
        Handle an agent failure.

        Args:
            agent_name: The name of the failed agent.
            error: The exception that occurred.

        Returns:
            Description of the action taken.
        """
        self.logger.warning(f"Agent {agent_name} failed: {error}")

        # Check for backup agent
        if agent_name in self._backup_agents:
            backup = self._backup_agents[agent_name]
            event = DegradationEvent(
                component=agent_name,
                action=DegradationAction.SWITCHED_BACKUP,
                level=DegradationLevel.MINOR,
                message=f"Switched from {agent_name} to backup agent {backup}",
                original_error=str(error),
            )
            self._record_event(event)
            return f"switched_to_backup:{backup}"

        # Check if critical
        if agent_name in self._critical_agents:
            event = DegradationEvent(
                component=agent_name,
                action=DegradationAction.FAILED,
                level=DegradationLevel.CRITICAL,
                message=f"Critical agent {agent_name} failed. Cannot continue.",
                original_error=str(error),
            )
            self._record_event(event)
            return "failed:critical_agent"

        # Skip non-critical task
        event = DegradationEvent(
            component=agent_name,
            action=DegradationAction.SKIPPED_TASK,
            level=DegradationLevel.MODERATE,
            message=f"Skipped non-critical agent {agent_name}",
            original_error=str(error),
        )
        self._record_event(event)
        return f"skipped:{agent_name}"

    async def on_api_failure(
        self,
        provider: str,
        error: Exception,
    ) -> str:
        """
        Handle an API provider failure.

        Args:
            provider: The name of the failed provider.
            error: The exception that occurred.

        Returns:
            Description of the action taken.
        """
        self.logger.warning(f"API provider {provider} failed: {error}")

        # Check for backup provider
        if provider in self._backup_providers:
            backup = self._backup_providers[provider]
            event = DegradationEvent(
                component=f"api:{provider}",
                action=DegradationAction.SWITCHED_BACKUP,
                level=DegradationLevel.MINOR,
                message=f"Switched from {provider} to backup provider {backup}",
                original_error=str(error),
            )
            self._record_event(event)
            return f"switched_to_backup:{backup}"

        # No backup available - continue with warning
        event = DegradationEvent(
            component=f"api:{provider}",
            action=DegradationAction.CONTINUED_WITH_WARNING,
            level=DegradationLevel.SEVERE,
            message=f"No backup for provider {provider}. Operations may fail.",
            original_error=str(error),
        )
        self._record_event(event)
        return f"warning:no_backup_for_{provider}"

    async def on_feature_unavailable(
        self,
        feature_name: str,
        fallback_behavior: str | None = None,
    ) -> str:
        """
        Handle a feature being unavailable.

        Args:
            feature_name: The name of the unavailable feature.
            fallback_behavior: Optional description of fallback.

        Returns:
            Description of the action taken.
        """
        if fallback_behavior:
            event = DegradationEvent(
                component=f"feature:{feature_name}",
                action=DegradationAction.USED_FALLBACK,
                level=DegradationLevel.MINOR,
                message=(
                    f"Feature {feature_name} unavailable. "
                    f"Using: {fallback_behavior}"
                ),
            )
            action = f"fallback:{fallback_behavior}"
        else:
            event = DegradationEvent(
                component=f"feature:{feature_name}",
                action=DegradationAction.SKIPPED_TASK,
                level=DegradationLevel.MODERATE,
                message=f"Feature {feature_name} unavailable and skipped.",
            )
            action = f"skipped:{feature_name}"

        self._record_event(event)
        return action

    def _record_event(self, event: DegradationEvent) -> None:
        """
        Record a degradation event and update current level.

        Args:
            event: The degradation event.
        """
        self._events.append(event)
        self._active_degradations[event.component] = event
        self._update_degradation_level()

        self.logger.info(
            f"Degradation: {event.action.value} for {event.component} "
            f"(level: {event.level.value})"
        )

    def _update_degradation_level(self) -> None:
        """Update the current overall degradation level."""
        if not self._active_degradations:
            self._current_level = DegradationLevel.NONE
            return

        # Find the highest severity level
        level_order = [
            DegradationLevel.NONE,
            DegradationLevel.MINOR,
            DegradationLevel.MODERATE,
            DegradationLevel.SEVERE,
            DegradationLevel.CRITICAL,
        ]

        max_level = DegradationLevel.NONE
        for event in self._active_degradations.values():
            if level_order.index(event.level) > level_order.index(max_level):
                max_level = event.level

        self._current_level = max_level

    def get_degradation_report(self) -> dict[str, Any]:
        """
        Get a report of all degradations that occurred.

        Returns:
            Dictionary with degradation report.
        """
        events_by_level: dict[str, int] = {}
        events_by_action: dict[str, int] = {}
        events_by_component: dict[str, list[dict[str, Any]]] = {}

        for event in self._events:
            # Count by level
            level = event.level.value
            events_by_level[level] = events_by_level.get(level, 0) + 1

            # Count by action
            action = event.action.value
            events_by_action[action] = events_by_action.get(action, 0) + 1

            # Group by component
            component = event.component
            if component not in events_by_component:
                events_by_component[component] = []
            events_by_component[component].append(event.to_dict())

        return {
            "current_level": self._current_level.value,
            "total_events": len(self._events),
            "active_degradations": len(self._active_degradations),
            "events_by_level": events_by_level,
            "events_by_action": events_by_action,
            "components_affected": list(self._active_degradations.keys()),
            "events_by_component": events_by_component,
            "backup_agents": dict(self._backup_agents),
            "backup_providers": dict(self._backup_providers),
        }

    def get_current_level(self) -> DegradationLevel:
        """
        Get the current degradation level.

        Returns:
            The current DegradationLevel.
        """
        return self._current_level

    def is_operational(self) -> bool:
        """
        Check if the system is still operational.

        Returns:
            True if system can continue, False if critical failure.
        """
        return self._current_level != DegradationLevel.CRITICAL

    def get_active_degradations(self) -> list[dict[str, Any]]:
        """
        Get list of currently active degradations.

        Returns:
            List of active degradation events.
        """
        return [event.to_dict() for event in self._active_degradations.values()]

    def clear_degradation(self, component: str) -> bool:
        """
        Clear a degradation (component recovered).

        Args:
            component: The component that recovered.

        Returns:
            True if degradation was cleared.
        """
        if component in self._active_degradations:
            del self._active_degradations[component]
            self._update_degradation_level()
            self.logger.info(f"Cleared degradation for {component}")
            return True
        return False

    def reset(self) -> None:
        """Reset all degradation tracking."""
        self._events.clear()
        self._active_degradations.clear()
        self._current_level = DegradationLevel.NONE
        self.logger.info("Reset degradation tracking")

    def get_events(self) -> list[dict[str, Any]]:
        """
        Get all degradation events.

        Returns:
            List of all degradation events.
        """
        return [event.to_dict() for event in self._events]
