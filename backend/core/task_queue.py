"""
AgentForge Studio - Task Queue.

This module implements a task distribution system for parallel execution
of agent tasks with priority support and dependency tracking.
"""

import asyncio
import logging
import threading
from collections import defaultdict
from datetime import datetime
from typing import Any

from backend.models.messages import Task, TaskPriority, TaskState


class TaskQueue:
    """
    Task queue for managing agent tasks with priority and dependency support.

    This class provides a thread-safe task queue that supports:
    - Task priorities (HIGH, MEDIUM, LOW)
    - Task states (PENDING, IN_PROGRESS, COMPLETED, FAILED, BLOCKED)
    - Task dependencies (task B waits for task A)
    - Parallel task execution tracking
    - Task timeout handling

    Attributes:
        tasks: Dictionary of all tasks by ID.
        agent_tasks: Dictionary mapping agents to their assigned tasks.

    Example:
        >>> queue = TaskQueue()
        >>> task = Task(id="1", type="create_html", description="Build homepage")
        >>> queue.add_task(task)
        >>> next_task = queue.get_next_task("frontend_agent")
    """

    def __init__(self, default_timeout: float = 300.0) -> None:
        """
        Initialize the task queue.

        Args:
            default_timeout: Default timeout in seconds for tasks
                without explicit timeout.
        """
        self._tasks: dict[str, Task] = {}
        self._agent_tasks: dict[str, set[str]] = defaultdict(set)
        self._pending_tasks: dict[TaskPriority, list[str]] = {
            TaskPriority.HIGH: [],
            TaskPriority.MEDIUM: [],
            TaskPriority.LOW: [],
        }
        self._default_timeout = default_timeout
        self._lock = threading.RLock()
        self.logger = logging.getLogger("task_queue")

    def add_task(self, task: Task) -> str:
        """
        Add a task to the queue.

        Args:
            task: The task to add.

        Returns:
            str: The task ID.
        """
        with self._lock:
            self._tasks[task.id] = task

            # Check if task is blocked by dependencies
            if self._has_unmet_dependencies(task):
                task.state = TaskState.BLOCKED
            else:
                # Add to pending queue by priority
                priority = TaskPriority(task.priority)
                self._pending_tasks[priority].append(task.id)

            self.logger.info(
                f"Added task {task.id} with priority {task.priority}, "
                f"state: {task.state}"
            )
            return task.id

    def get_task(self, task_id: str) -> Task | None:
        """
        Get a task by ID.

        Args:
            task_id: The task ID.

        Returns:
            The task or None if not found.
        """
        with self._lock:
            return self._tasks.get(task_id)

    def get_next_task(self, agent: str) -> Task | None:
        """
        Get the next available task for an agent.

        Returns the highest priority pending task that the agent can work on.

        Args:
            agent: Name of the agent requesting a task.

        Returns:
            The next available task or None if no tasks available.
        """
        with self._lock:
            # Check for timed out tasks first
            self._check_timeouts()

            # Try to get task in priority order
            for priority in [TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.LOW]:
                pending_list = self._pending_tasks[priority]
                for task_id in pending_list[:]:  # Copy to allow modification
                    task = self._tasks.get(task_id)
                    if task and task.state == TaskState.PENDING:
                        if not self._has_unmet_dependencies(task):
                            # Assign task to agent
                            task.agent = agent
                            task.state = TaskState.IN_PROGRESS
                            task.started_at = datetime.utcnow()
                            pending_list.remove(task_id)
                            self._agent_tasks[agent].add(task_id)

                            self.logger.info(
                                f"Assigned task {task_id} to agent {agent}"
                            )
                            return task

            return None

    def complete_task(
        self,
        task_id: str,
        result: Any = None,
        error: str | None = None,
    ) -> bool:
        """
        Mark a task as completed or failed.

        Args:
            task_id: The task ID.
            result: Optional result data.
            error: Optional error message (sets state to FAILED).

        Returns:
            bool: True if task was updated, False if not found.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            task.completed_at = datetime.utcnow()
            task.result = result

            if error:
                task.state = TaskState.FAILED
                task.error = error
                self.logger.warning(f"Task {task_id} failed: {error}")
            else:
                task.state = TaskState.COMPLETED
                self.logger.info(f"Task {task_id} completed")

            # Remove from agent tasks
            if task.agent:
                self._agent_tasks[task.agent].discard(task_id)

            # Unblock dependent tasks
            self._update_blocked_tasks(task_id)

            return True

    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a pending task.

        Args:
            task_id: The task ID.

        Returns:
            bool: True if task was cancelled, False if not found or already started.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            if task.state != TaskState.PENDING:
                self.logger.warning(
                    f"Cannot cancel task {task_id} in state {task.state}"
                )
                return False

            task.state = TaskState.FAILED
            task.error = "Cancelled"
            task.completed_at = datetime.utcnow()

            # Remove from pending queue
            priority = TaskPriority(task.priority)
            if task_id in self._pending_tasks[priority]:
                self._pending_tasks[priority].remove(task_id)

            self.logger.info(f"Cancelled task {task_id}")
            return True

    def get_agent_tasks(self, agent: str) -> list[Task]:
        """
        Get all tasks assigned to an agent.

        Args:
            agent: Agent name.

        Returns:
            List of tasks assigned to the agent.
        """
        with self._lock:
            task_ids = self._agent_tasks.get(agent, set())
            return [self._tasks[tid] for tid in task_ids if tid in self._tasks]

    def get_tasks_by_state(self, state: TaskState) -> list[Task]:
        """
        Get all tasks in a specific state.

        Args:
            state: The task state to filter by.

        Returns:
            List of tasks in the specified state.
        """
        with self._lock:
            return [t for t in self._tasks.values() if t.state == state]

    def get_pending_count(self) -> int:
        """
        Get the number of pending tasks.

        Returns:
            int: Number of pending tasks.
        """
        with self._lock:
            return sum(len(q) for q in self._pending_tasks.values())

    def get_all_tasks(self) -> list[Task]:
        """
        Get all tasks in the queue.

        Returns:
            List of all tasks.
        """
        with self._lock:
            return list(self._tasks.values())

    def clear(self) -> None:
        """Clear all tasks from the queue."""
        with self._lock:
            self._tasks.clear()
            self._agent_tasks.clear()
            for priority in self._pending_tasks:
                self._pending_tasks[priority].clear()
            self.logger.info("Task queue cleared")

    def _has_unmet_dependencies(self, task: Task) -> bool:
        """
        Check if a task has unmet dependencies.

        Args:
            task: The task to check.

        Returns:
            bool: True if task has dependencies that are not completed.
        """
        for dep_id in task.dependencies:
            dep_task = self._tasks.get(dep_id)
            if not dep_task or dep_task.state != TaskState.COMPLETED:
                return True
        return False

    def _update_blocked_tasks(self, completed_task_id: str) -> None:
        """
        Update blocked tasks when a dependency completes.

        Args:
            completed_task_id: ID of the task that just completed.
        """
        for task in self._tasks.values():
            if task.state == TaskState.BLOCKED:
                if completed_task_id in task.dependencies:
                    if not self._has_unmet_dependencies(task):
                        task.state = TaskState.PENDING
                        priority = TaskPriority(task.priority)
                        self._pending_tasks[priority].append(task.id)
                        self.logger.info(
                            f"Task {task.id} unblocked, moved to pending"
                        )

    def _check_timeouts(self) -> None:
        """Check for and handle timed out tasks."""
        now = datetime.utcnow()
        for task in self._tasks.values():
            if task.state == TaskState.IN_PROGRESS and task.started_at:
                timeout = task.timeout or self._default_timeout
                elapsed = (now - task.started_at).total_seconds()
                if elapsed > timeout:
                    task.state = TaskState.FAILED
                    task.error = f"Task timed out after {timeout} seconds"
                    task.completed_at = now
                    if task.agent:
                        self._agent_tasks[task.agent].discard(task.id)
                    self.logger.warning(f"Task {task.id} timed out")


class AsyncTaskQueue:
    """
    Async wrapper for TaskQueue with additional async functionality.

    This class provides async methods for task queue operations and
    supports waiting for task completion.

    Example:
        >>> queue = AsyncTaskQueue()
        >>> task = Task(id="1", type="create_html", description="Build homepage")
        >>> await queue.add_task(task)
        >>> result = await queue.wait_for_task("1", timeout=30.0)
    """

    def __init__(self, default_timeout: float = 300.0) -> None:
        """
        Initialize the async task queue.

        Args:
            default_timeout: Default timeout in seconds for tasks.
        """
        self._queue = TaskQueue(default_timeout)
        self._completion_events: dict[str, asyncio.Event] = {}
        self._lock = asyncio.Lock()

    async def add_task(self, task: Task) -> str:
        """
        Add a task to the queue.

        Args:
            task: The task to add.

        Returns:
            str: The task ID.
        """
        async with self._lock:
            self._completion_events[task.id] = asyncio.Event()
            return self._queue.add_task(task)

    async def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        return self._queue.get_task(task_id)

    async def get_next_task(self, agent: str) -> Task | None:
        """Get the next available task for an agent."""
        return self._queue.get_next_task(agent)

    async def complete_task(
        self,
        task_id: str,
        result: Any = None,
        error: str | None = None,
    ) -> bool:
        """
        Mark a task as completed or failed.

        Args:
            task_id: The task ID.
            result: Optional result data.
            error: Optional error message (sets state to FAILED).

        Returns:
            bool: True if task was updated, False if not found.
        """
        async with self._lock:
            success = self._queue.complete_task(task_id, result, error)
            if success and task_id in self._completion_events:
                self._completion_events[task_id].set()
            return success

    async def wait_for_task(
        self,
        task_id: str,
        timeout: float | None = None,
    ) -> Task | None:
        """
        Wait for a task to complete.

        Args:
            task_id: The task ID to wait for.
            timeout: Optional timeout in seconds.

        Returns:
            The completed task or None if timeout or not found.
        """
        event = self._completion_events.get(task_id)
        if not event:
            return None

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return self._queue.get_task(task_id)
        except asyncio.TimeoutError:
            return None

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task."""
        return self._queue.cancel_task(task_id)

    async def get_agent_tasks(self, agent: str) -> list[Task]:
        """Get all tasks assigned to an agent."""
        return self._queue.get_agent_tasks(agent)

    async def get_tasks_by_state(self, state: TaskState) -> list[Task]:
        """Get all tasks in a specific state."""
        return self._queue.get_tasks_by_state(state)

    async def get_pending_count(self) -> int:
        """Get the number of pending tasks."""
        return self._queue.get_pending_count()

    async def get_all_tasks(self) -> list[Task]:
        """Get all tasks in the queue."""
        return self._queue.get_all_tasks()

    async def clear(self) -> None:
        """Clear all tasks from the queue."""
        async with self._lock:
            self._queue.clear()
            self._completion_events.clear()
