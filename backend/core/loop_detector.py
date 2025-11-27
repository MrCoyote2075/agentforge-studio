"""
AgentForge Studio - Loop Detector.

This module implements loop detection to prevent infinite retries
when agents keep failing on the same task.
"""

import logging
from datetime import datetime
from typing import Any


class LoopDetector:
    """
    Detects infinite loops when tasks keep failing.

    Tracks task attempts and prevents infinite retries by enforcing
    a maximum number of attempts per task.

    Attributes:
        max_retries: Maximum number of retries allowed per task.
        task_attempts: Dictionary tracking task_id -> attempt count.
        failed_tasks: Set of task IDs that exceeded max retries.
        logger: Logger instance.

    Example:
        >>> detector = LoopDetector(max_retries=3)
        >>> detector.record_attempt("task-1")
        1
        >>> detector.should_retry("task-1")
        True
    """

    def __init__(self, max_retries: int = 3) -> None:
        """
        Initialize the LoopDetector.

        Args:
            max_retries: Maximum number of retries allowed per task.
                        Defaults to 3.
        """
        self.max_retries = max_retries
        self._task_attempts: dict[str, int] = {}
        self._failed_tasks: set[str] = set()
        self._task_metadata: dict[str, dict[str, Any]] = {}
        self.logger = logging.getLogger("loop_detector")

    def record_attempt(self, task_id: str) -> int:
        """
        Record an attempt for a task.

        Args:
            task_id: The unique identifier of the task.

        Returns:
            The current attempt count for the task.
        """
        if task_id not in self._task_attempts:
            self._task_attempts[task_id] = 0
            self._task_metadata[task_id] = {
                "first_attempt": datetime.utcnow(),
                "last_attempt": datetime.utcnow(),
            }

        self._task_attempts[task_id] += 1
        self._task_metadata[task_id]["last_attempt"] = datetime.utcnow()

        current_count = self._task_attempts[task_id]
        self.logger.debug(f"Task {task_id}: attempt {current_count}/{self.max_retries}")

        # Mark as failed if we've exceeded max retries
        if current_count > self.max_retries:
            self._failed_tasks.add(task_id)
            self.logger.warning(
                f"Task {task_id} exceeded max retries ({self.max_retries})"
            )

        return current_count

    def should_retry(self, task_id: str) -> bool:
        """
        Check if a task can be retried.

        Args:
            task_id: The unique identifier of the task.

        Returns:
            True if the task can be retried, False otherwise.
        """
        attempts = self._task_attempts.get(task_id, 0)
        can_retry = attempts <= self.max_retries

        if not can_retry:
            self.logger.debug(
                f"Task {task_id} cannot retry: {attempts}/{self.max_retries} attempts"
            )

        return can_retry

    def reset(self, task_id: str) -> None:
        """
        Reset the counter for a task after success.

        Args:
            task_id: The unique identifier of the task.
        """
        if task_id in self._task_attempts:
            self._task_attempts.pop(task_id)
            self._failed_tasks.discard(task_id)
            self._task_metadata.pop(task_id, None)
            self.logger.debug(f"Reset attempt counter for task {task_id}")

    def get_failed_tasks(self) -> list[str]:
        """
        Get list of tasks that exceeded max retries.

        Returns:
            List of task IDs that failed due to too many retries.
        """
        return list(self._failed_tasks)

    def get_attempt_count(self, task_id: str) -> int:
        """
        Get the current attempt count for a task.

        Args:
            task_id: The unique identifier of the task.

        Returns:
            The number of attempts made for the task.
        """
        return self._task_attempts.get(task_id, 0)

    def get_task_info(self, task_id: str) -> dict[str, Any] | None:
        """
        Get detailed info about a task's retry history.

        Args:
            task_id: The unique identifier of the task.

        Returns:
            Dictionary with task info or None if task not found.
        """
        if task_id not in self._task_attempts:
            return None

        metadata = self._task_metadata.get(task_id, {})
        return {
            "task_id": task_id,
            "attempt_count": self._task_attempts[task_id],
            "max_retries": self.max_retries,
            "is_failed": task_id in self._failed_tasks,
            "can_retry": self.should_retry(task_id),
            "first_attempt": metadata.get("first_attempt"),
            "last_attempt": metadata.get("last_attempt"),
        }

    def configure_max_retries(self, max_retries: int) -> None:
        """
        Configure the maximum number of retries.

        Args:
            max_retries: New maximum number of retries.
        """
        self.max_retries = max_retries
        self.logger.info(f"Max retries configured to {max_retries}")

    def clear(self) -> None:
        """Clear all tracking data."""
        self._task_attempts.clear()
        self._failed_tasks.clear()
        self._task_metadata.clear()
        self.logger.debug("Cleared all loop detection data")

    def get_stats(self) -> dict[str, Any]:
        """
        Get statistics about loop detection.

        Returns:
            Dictionary with loop detection statistics.
        """
        return {
            "total_tracked_tasks": len(self._task_attempts),
            "failed_tasks_count": len(self._failed_tasks),
            "max_retries": self.max_retries,
            "tasks_by_attempts": self._get_tasks_by_attempts(),
        }

    def _get_tasks_by_attempts(self) -> dict[int, int]:
        """
        Get count of tasks grouped by attempt count.

        Returns:
            Dictionary mapping attempt count -> number of tasks.
        """
        counts: dict[int, int] = {}
        for attempts in self._task_attempts.values():
            counts[attempts] = counts.get(attempts, 0) + 1
        return counts
