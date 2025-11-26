"""
AgentForge Studio - Task Dispatcher.

This module implements parallel task execution and coordination
for distributing work across multiple agents.
"""

import asyncio
import logging
from collections.abc import Callable, Coroutine
from datetime import datetime
from enum import Enum
from typing import Any

from backend.models.project import DevelopmentPlan, PlanTask


class DispatchedTaskState(str, Enum):
    """State of a dispatched task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DispatchedTask:
    """
    Represents a task that has been dispatched for execution.

    Attributes:
        id: Task identifier.
        plan_task: The original plan task.
        state: Current execution state.
        result: Task result when completed.
        error: Error message if failed.
        started_at: When task execution started.
        completed_at: When task execution completed.
    """

    def __init__(self, plan_task: PlanTask) -> None:
        """
        Initialize a dispatched task.

        Args:
            plan_task: The plan task to execute.
        """
        self.id = plan_task.id
        self.plan_task = plan_task
        self.state = DispatchedTaskState.PENDING
        self.result: Any = None
        self.error: str | None = None
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None


# Type alias for task executor functions
TaskExecutor = Callable[
    [str, PlanTask], Coroutine[Any, Any, dict[str, Any]]
]


class TaskDispatcher:
    """
    Dispatcher for parallel task execution.

    This class manages the distribution and parallel execution of tasks,
    respecting dependencies and tracking completion status.

    Attributes:
        tasks: Dictionary of dispatched tasks by ID.
        logger: Logger instance.

    Example:
        >>> dispatcher = TaskDispatcher()
        >>> await dispatcher.dispatch_plan("proj-1", plan)
        >>> await dispatcher.execute_parallel_tasks("proj-1", executor)
    """

    def __init__(self, max_parallel_tasks: int = 5) -> None:
        """
        Initialize the task dispatcher.

        Args:
            max_parallel_tasks: Maximum number of tasks to run in parallel.
        """
        # project_id -> task_id -> task
        self._tasks: dict[str, dict[str, DispatchedTask]] = {}
        self._max_parallel = max_parallel_tasks
        self._semaphore = asyncio.Semaphore(max_parallel_tasks)
        self.logger = logging.getLogger("task_dispatcher")

    def dispatch_plan(
        self,
        project_id: str,
        plan: DevelopmentPlan,
    ) -> list[DispatchedTask]:
        """
        Dispatch all tasks from a development plan.

        Args:
            project_id: Project identifier.
            plan: Development plan with tasks.

        Returns:
            List of dispatched tasks.
        """
        if project_id not in self._tasks:
            self._tasks[project_id] = {}

        dispatched = []
        for task in plan.tasks:
            dispatched_task = DispatchedTask(task)
            self._tasks[project_id][task.id] = dispatched_task
            dispatched.append(dispatched_task)
            self.logger.info(
                f"Dispatched task {task.id} for project {project_id}: "
                f"{task.description[:50]}"
            )

        return dispatched

    async def execute_parallel_tasks(
        self,
        project_id: str,
        executor: TaskExecutor,
    ) -> dict[str, Any]:
        """
        Execute all pending tasks in parallel respecting dependencies.

        Args:
            project_id: Project identifier.
            executor: Async function to execute each task.

        Returns:
            Dictionary of task results by task ID.
        """
        if project_id not in self._tasks:
            return {}

        results: dict[str, Any] = {}
        tasks_dict = self._tasks[project_id]

        # Build dependency graph
        pending_tasks = {
            task_id: task
            for task_id, task in tasks_dict.items()
            if task.state == DispatchedTaskState.PENDING
        }

        # Execute tasks in waves respecting dependencies
        while pending_tasks:
            # Find tasks with all dependencies satisfied
            ready_tasks = []
            for task_id, task in list(pending_tasks.items()):
                deps = task.plan_task.dependencies
                all_deps_complete = all(
                    tasks_dict.get(dep_id, DispatchedTask(
                        PlanTask(description="", assigned_to="")
                    )).state == DispatchedTaskState.COMPLETED
                    for dep_id in deps
                )
                # Also check that no dependency has failed
                any_dep_failed = any(
                    tasks_dict.get(dep_id, DispatchedTask(
                        PlanTask(description="", assigned_to="")
                    )).state == DispatchedTaskState.FAILED
                    for dep_id in deps
                )

                if any_dep_failed:
                    task.state = DispatchedTaskState.FAILED
                    task.error = "Dependency failed"
                    task.completed_at = datetime.utcnow()
                    del pending_tasks[task_id]
                elif all_deps_complete or not deps:
                    ready_tasks.append(task)

            if not ready_tasks:
                # No tasks ready, but still have pending - might be circular deps
                if pending_tasks:
                    self.logger.warning(
                        f"Possible circular dependencies in project {project_id}"
                    )
                    for task in pending_tasks.values():
                        task.state = DispatchedTaskState.FAILED
                        task.error = "Circular dependency detected"
                break

            # Execute ready tasks in parallel
            async def run_task(task: DispatchedTask) -> None:
                async with self._semaphore:
                    await self._execute_single_task(
                        project_id, task, executor, results
                    )

            await asyncio.gather(*[run_task(t) for t in ready_tasks])

            # Remove completed tasks from pending
            for task in ready_tasks:
                if task.id in pending_tasks:
                    del pending_tasks[task.id]

        return results

    async def _execute_single_task(
        self,
        project_id: str,
        task: DispatchedTask,
        executor: TaskExecutor,
        results: dict[str, Any],
    ) -> None:
        """
        Execute a single task.

        Args:
            project_id: Project identifier.
            task: Task to execute.
            executor: Executor function.
            results: Results dictionary to update.
        """
        task.state = DispatchedTaskState.RUNNING
        task.started_at = datetime.utcnow()

        self.logger.info(f"Starting task {task.id} for project {project_id}")

        try:
            result = await executor(project_id, task.plan_task)
            task.state = DispatchedTaskState.COMPLETED
            task.result = result
            task.completed_at = datetime.utcnow()
            results[task.id] = result

            self.logger.info(f"Completed task {task.id} for project {project_id}")

        except Exception as e:
            task.state = DispatchedTaskState.FAILED
            task.error = str(e)
            task.completed_at = datetime.utcnow()
            results[task.id] = {"error": str(e)}

            self.logger.error(
                f"Task {task.id} failed for project {project_id}: {e}"
            )

    def handle_task_completion(
        self,
        task_id: str,
        result: Any,
        project_id: str | None = None,
    ) -> bool:
        """
        Handle completion of a task.

        Args:
            task_id: Task identifier.
            result: Task result.
            project_id: Optional project ID. If not provided,
                        searches all projects.

        Returns:
            True if task was found and updated, False otherwise.
        """
        if project_id:
            tasks = self._tasks.get(project_id, {})
            if task_id in tasks:
                task = tasks[task_id]
                task.state = DispatchedTaskState.COMPLETED
                task.result = result
                task.completed_at = datetime.utcnow()
                return True
            return False

        # Search all projects
        for tasks in self._tasks.values():
            if task_id in tasks:
                task = tasks[task_id]
                task.state = DispatchedTaskState.COMPLETED
                task.result = result
                task.completed_at = datetime.utcnow()
                return True
        return False

    def handle_task_failure(
        self,
        task_id: str,
        error: str,
        project_id: str | None = None,
    ) -> bool:
        """
        Handle failure of a task.

        Args:
            task_id: Task identifier.
            error: Error message.
            project_id: Optional project ID.

        Returns:
            True if task was found and updated, False otherwise.
        """
        if project_id:
            tasks = self._tasks.get(project_id, {})
            if task_id in tasks:
                task = tasks[task_id]
                task.state = DispatchedTaskState.FAILED
                task.error = error
                task.completed_at = datetime.utcnow()
                return True
            return False

        # Search all projects
        for tasks in self._tasks.values():
            if task_id in tasks:
                task = tasks[task_id]
                task.state = DispatchedTaskState.FAILED
                task.error = error
                task.completed_at = datetime.utcnow()
                return True
        return False

    def cancel_task(
        self,
        task_id: str,
        project_id: str | None = None,
    ) -> bool:
        """
        Cancel a pending task.

        Args:
            task_id: Task identifier.
            project_id: Optional project ID.

        Returns:
            True if task was cancelled, False if not found or already started.
        """
        if project_id:
            tasks = self._tasks.get(project_id, {})
            if task_id in tasks:
                task = tasks[task_id]
                if task.state == DispatchedTaskState.PENDING:
                    task.state = DispatchedTaskState.CANCELLED
                    task.completed_at = datetime.utcnow()
                    return True
            return False

        # Search all projects
        for tasks in self._tasks.values():
            if task_id in tasks:
                task = tasks[task_id]
                if task.state == DispatchedTaskState.PENDING:
                    task.state = DispatchedTaskState.CANCELLED
                    task.completed_at = datetime.utcnow()
                    return True
        return False

    def get_task_status(
        self,
        task_id: str,
        project_id: str | None = None,
    ) -> DispatchedTask | None:
        """
        Get the status of a task.

        Args:
            task_id: Task identifier.
            project_id: Optional project ID.

        Returns:
            The task or None if not found.
        """
        if project_id:
            tasks = self._tasks.get(project_id, {})
            return tasks.get(task_id)

        # Search all projects
        for tasks in self._tasks.values():
            if task_id in tasks:
                return tasks[task_id]
        return None

    def get_project_tasks(self, project_id: str) -> list[DispatchedTask]:
        """
        Get all tasks for a project.

        Args:
            project_id: Project identifier.

        Returns:
            List of dispatched tasks.
        """
        tasks = self._tasks.get(project_id, {})
        return list(tasks.values())

    def get_pending_tasks(self, project_id: str) -> list[DispatchedTask]:
        """
        Get all pending tasks for a project.

        Args:
            project_id: Project identifier.

        Returns:
            List of pending tasks.
        """
        tasks = self._tasks.get(project_id, {})
        return [t for t in tasks.values() if t.state == DispatchedTaskState.PENDING]

    def get_running_tasks(self, project_id: str) -> list[DispatchedTask]:
        """
        Get all running tasks for a project.

        Args:
            project_id: Project identifier.

        Returns:
            List of running tasks.
        """
        tasks = self._tasks.get(project_id, {})
        return [t for t in tasks.values() if t.state == DispatchedTaskState.RUNNING]

    def get_completed_tasks(self, project_id: str) -> list[DispatchedTask]:
        """
        Get all completed tasks for a project.

        Args:
            project_id: Project identifier.

        Returns:
            List of completed tasks.
        """
        tasks = self._tasks.get(project_id, {})
        return [
            t for t in tasks.values()
            if t.state == DispatchedTaskState.COMPLETED
        ]

    def get_failed_tasks(self, project_id: str) -> list[DispatchedTask]:
        """
        Get all failed tasks for a project.

        Args:
            project_id: Project identifier.

        Returns:
            List of failed tasks.
        """
        tasks = self._tasks.get(project_id, {})
        return [t for t in tasks.values() if t.state == DispatchedTaskState.FAILED]

    def is_project_complete(self, project_id: str) -> bool:
        """
        Check if all tasks for a project are complete.

        Args:
            project_id: Project identifier.

        Returns:
            True if all tasks are in a terminal state.
        """
        tasks = self._tasks.get(project_id, {})
        if not tasks:
            return True

        terminal_states = {
            DispatchedTaskState.COMPLETED,
            DispatchedTaskState.FAILED,
            DispatchedTaskState.CANCELLED,
        }
        return all(t.state in terminal_states for t in tasks.values())

    def is_project_successful(self, project_id: str) -> bool:
        """
        Check if all tasks for a project completed successfully.

        Args:
            project_id: Project identifier.

        Returns:
            True if all tasks completed without failure.
        """
        tasks = self._tasks.get(project_id, {})
        if not tasks:
            return True

        return all(
            t.state == DispatchedTaskState.COMPLETED
            for t in tasks.values()
        )

    def clear_project(self, project_id: str) -> None:
        """
        Clear all tasks for a project.

        Args:
            project_id: Project identifier.
        """
        if project_id in self._tasks:
            del self._tasks[project_id]
            self.logger.info(f"Cleared tasks for project {project_id}")

    def clear(self) -> None:
        """Clear all tasks."""
        self._tasks.clear()
        self.logger.info("Task dispatcher cleared")
