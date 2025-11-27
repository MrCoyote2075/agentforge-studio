"""
AgentForge Studio - Timeout Manager.

This module implements timeout management for handling hanging operations
with configurable timeouts for different operation types.
"""

import asyncio
import logging
from collections.abc import Coroutine
from datetime import datetime
from typing import Any, TypeVar

T = TypeVar("T")


class TimeoutError(Exception):
    """Exception raised when an operation times out."""

    def __init__(
        self,
        message: str,
        timeout_type: str,
        timeout_seconds: int,
        task_id: str | None = None,
    ) -> None:
        """
        Initialize TimeoutError.

        Args:
            message: Error message.
            timeout_type: Type of timeout (api_call, task, stage, project).
            timeout_seconds: The timeout value that was exceeded.
            task_id: Optional task identifier.
        """
        super().__init__(message)
        self.timeout_type = timeout_type
        self.timeout_seconds = timeout_seconds
        self.task_id = task_id
        self.timestamp = datetime.utcnow()


class TimeoutManager:
    """
    Manages timeouts for different operation types.

    Provides configurable timeout handling for API calls, tasks,
    stages, and entire projects.

    Attributes:
        timeouts: Dictionary of timeout type -> seconds.
        logger: Logger instance.

    Example:
        >>> manager = TimeoutManager()
        >>> result = await manager.run_with_timeout(
        ...     some_coroutine(),
        ...     timeout_type="api_call",
        ...     task_id="task-1"
        ... )
    """

    # Default timeout values in seconds
    DEFAULT_TIMEOUTS = {
        "api_call": 60,  # 1 minute
        "task": 300,  # 5 minutes
        "stage": 1800,  # 30 minutes
        "project": 7200,  # 2 hours
    }

    def __init__(self) -> None:
        """Initialize the TimeoutManager with default timeouts."""
        self.timeouts = self.DEFAULT_TIMEOUTS.copy()
        self._active_operations: dict[str, dict[str, Any]] = {}
        self._timeout_events: list[dict[str, Any]] = []
        self.logger = logging.getLogger("timeout_manager")

    async def run_with_timeout(
        self,
        coro: Coroutine[Any, Any, T],
        timeout_type: str,
        task_id: str | None = None,
    ) -> T:
        """
        Run a coroutine with timeout.

        Args:
            coro: The coroutine to run.
            timeout_type: Type of timeout to apply.
            task_id: Optional task identifier for tracking.

        Returns:
            The result of the coroutine.

        Raises:
            TimeoutError: If the operation times out.
            ValueError: If the timeout_type is not valid.
        """
        if timeout_type not in self.timeouts:
            raise ValueError(
                f"Unknown timeout type: {timeout_type}. "
                f"Valid types: {list(self.timeouts.keys())}"
            )

        timeout_seconds = self.timeouts[timeout_type]
        operation_id = task_id or f"{timeout_type}_{datetime.utcnow().timestamp()}"

        # Track the operation
        self._active_operations[operation_id] = {
            "timeout_type": timeout_type,
            "timeout_seconds": timeout_seconds,
            "started_at": datetime.utcnow(),
            "task_id": task_id,
        }

        self.logger.debug(
            f"Starting {timeout_type} operation {operation_id} "
            f"with {timeout_seconds}s timeout"
        )

        try:
            result = await asyncio.wait_for(coro, timeout=timeout_seconds)
            self.logger.debug(f"Operation {operation_id} completed successfully")
            return result

        except asyncio.TimeoutError:
            # Record the timeout event
            timeout_event = {
                "operation_id": operation_id,
                "timeout_type": timeout_type,
                "timeout_seconds": timeout_seconds,
                "task_id": task_id,
                "timestamp": datetime.utcnow(),
            }
            self._timeout_events.append(timeout_event)

            self.logger.warning(
                f"Operation {operation_id} timed out after {timeout_seconds}s"
            )

            raise TimeoutError(
                f"Operation timed out after {timeout_seconds} seconds",
                timeout_type=timeout_type,
                timeout_seconds=timeout_seconds,
                task_id=task_id,
            ) from None

        finally:
            # Remove from active operations
            self._active_operations.pop(operation_id, None)

    def configure_timeout(self, timeout_type: str, seconds: int) -> None:
        """
        Configure timeout for a type.

        Args:
            timeout_type: The type of timeout to configure.
            seconds: The timeout value in seconds.

        Raises:
            ValueError: If seconds is not positive.
        """
        if seconds <= 0:
            raise ValueError("Timeout must be a positive number")

        self.timeouts[timeout_type] = seconds
        self.logger.info(f"Configured {timeout_type} timeout to {seconds}s")

    def get_timeout(self, timeout_type: str) -> int | None:
        """
        Get the timeout value for a type.

        Args:
            timeout_type: The type of timeout.

        Returns:
            The timeout in seconds, or None if type not found.
        """
        return self.timeouts.get(timeout_type)

    def get_active_operations(self) -> list[dict[str, Any]]:
        """
        Get list of currently active operations.

        Returns:
            List of active operation details.
        """
        now = datetime.utcnow()
        result = []
        for op_id, op_data in self._active_operations.items():
            elapsed = (now - op_data["started_at"]).total_seconds()
            result.append({
                "operation_id": op_id,
                **op_data,
                "elapsed_seconds": elapsed,
                "remaining_seconds": max(0, op_data["timeout_seconds"] - elapsed),
            })
        return result

    def get_timeout_events(self) -> list[dict[str, Any]]:
        """
        Get list of timeout events that occurred.

        Returns:
            List of timeout event details.
        """
        return list(self._timeout_events)

    def get_stats(self) -> dict[str, Any]:
        """
        Get timeout statistics.

        Returns:
            Dictionary with timeout statistics.
        """
        events_by_type: dict[str, int] = {}
        for event in self._timeout_events:
            t_type = event["timeout_type"]
            events_by_type[t_type] = events_by_type.get(t_type, 0) + 1

        return {
            "configured_timeouts": dict(self.timeouts),
            "active_operations": len(self._active_operations),
            "total_timeout_events": len(self._timeout_events),
            "timeout_events_by_type": events_by_type,
        }

    def clear_events(self) -> None:
        """Clear recorded timeout events."""
        self._timeout_events.clear()
        self.logger.debug("Cleared timeout events")

    def reset_to_defaults(self) -> None:
        """Reset all timeouts to default values."""
        self.timeouts = self.DEFAULT_TIMEOUTS.copy()
        self.logger.info("Reset timeouts to defaults")

    async def cancel_operation(self, operation_id: str) -> bool:
        """
        Cancel an active operation.

        Note: This only marks the operation as cancelled in our tracking.
        The actual cancellation of the coroutine should be handled
        by the caller using asyncio task cancellation.

        Args:
            operation_id: The operation to cancel.

        Returns:
            True if operation was found and removed.
        """
        if operation_id in self._active_operations:
            self._active_operations.pop(operation_id)
            self.logger.info(f"Cancelled operation {operation_id}")
            return True
        return False
