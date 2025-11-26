"""
AgentForge Studio - Orchestrator.

This module implements the main Orchestrator class that coordinates
all agents and manages the complete development workflow.
"""

import logging
from datetime import datetime
from typing import Any

from backend.core.agent_registry import AgentRegistry
from backend.core.event_emitter import EventEmitter
from backend.core.message_bus import MessageBus
from backend.core.project_manager import ProjectManager
from backend.core.task_dispatcher import TaskDispatcher
from backend.core.task_queue import AsyncTaskQueue
from backend.core.workflow_engine import WorkflowEngine
from backend.models.project import (
    DevelopmentPlan,
    PlanTask,
    ProjectRequirements,
    ProjectStage,
)
from backend.models.project import (
    Project as WfProject,
)


class Orchestrator:
    """
    Main coordinator for the AgentForge Studio development workflow.

    The Orchestrator manages all agents, coordinates their activities,
    routes messages between them, and tracks project progress through
    the complete development lifecycle.

    Attributes:
        workflow_engine: Manages project stage transitions.
        project_manager: Handles project data management.
        task_dispatcher: Coordinates parallel task execution.
        message_bus: Handles inter-agent communication.
        event_emitter: Emits events for UI updates.
        agent_registry: Tracks agent status and capabilities.
        task_queue: Manages task queueing.
        logger: Logger instance.

    Example:
        >>> orchestrator = Orchestrator()
        >>> await orchestrator.initialize()
        >>> project = await orchestrator.start_project("proj-1", "Build a website")
    """

    def __init__(
        self,
        message_bus: MessageBus | None = None,
        event_emitter: EventEmitter | None = None,
        agent_registry: AgentRegistry | None = None,
        task_queue: AsyncTaskQueue | None = None,
    ) -> None:
        """
        Initialize the Orchestrator.

        Args:
            message_bus: Optional message bus instance.
            event_emitter: Optional event emitter instance.
            agent_registry: Optional agent registry instance.
            task_queue: Optional task queue instance.
        """
        # Core components
        self.workflow_engine = WorkflowEngine()
        self.project_manager = ProjectManager()
        self.task_dispatcher = TaskDispatcher()

        # External components (can be injected)
        self.message_bus = message_bus or MessageBus()
        self.event_emitter = event_emitter or EventEmitter()
        self.agent_registry = agent_registry or AgentRegistry()
        self.task_queue = task_queue or AsyncTaskQueue()

        # Agent references (to be set during initialization)
        self._agents: dict[str, Any] = {}

        # Execution state
        self._running = False

        self.logger = logging.getLogger("orchestrator")

    async def initialize(self) -> None:
        """
        Initialize the orchestrator and its components.

        This starts the message bus, event emitter, and agent registry
        health check.
        """
        await self.message_bus.start()
        await self.event_emitter.start()
        await self.agent_registry.start_health_check()
        self._running = True
        self.logger.info("Orchestrator initialized")

    async def shutdown(self) -> None:
        """
        Shutdown the orchestrator and its components.

        This stops all background tasks and cleans up resources.
        """
        self._running = False
        await self.message_bus.stop()
        await self.event_emitter.stop()
        await self.agent_registry.stop_health_check()
        self.logger.info("Orchestrator shutdown")

    def register_agent(self, name: str, agent: Any, capabilities: list[str]) -> None:
        """
        Register an agent with the orchestrator.

        Args:
            name: Agent name.
            agent: Agent instance.
            capabilities: List of agent capabilities.
        """
        self._agents[name] = agent
        self.agent_registry.register(name, capabilities=capabilities)
        self.logger.info(f"Registered agent: {name}")

    async def start_project(
        self,
        project_id: str,
        initial_message: str,
    ) -> dict[str, Any]:
        """
        Start a new project.

        Args:
            project_id: Unique project identifier.
            initial_message: Initial project request from client.

        Returns:
            Dictionary with project info and status.
        """
        try:
            # Create project in workflow engine
            project = self.workflow_engine.create_project(
                project_id=project_id,
                name=f"Project-{project_id[:8]}",
            )

            # Also create in project manager for data storage
            pm_project = WfProject(
                id=project_id,
                name=project.name,
                description=initial_message[:200],
                stage=ProjectStage.INITIALIZED,
            )
            self.project_manager._projects[project_id] = pm_project

            # Store initial requirements
            requirements = ProjectRequirements(
                original_request=initial_message,
            )
            self.project_manager.update_requirements(project_id, requirements)

            # Add initial message to conversation history
            self.project_manager.add_conversation_message(
                project_id, "user", initial_message
            )

            # Transition to requirements gathering
            self.workflow_engine.transition(
                project_id,
                ProjectStage.REQUIREMENTS_GATHERING,
                "Project started",
            )

            # Emit project_created event
            await self.event_emitter.emit(
                "project_created",
                {
                    "project_id": project_id,
                    "name": project.name,
                    "initial_message": initial_message[:100],
                },
                source="orchestrator",
            )

            self.logger.info(f"Started project {project_id}")

            return {
                "project_id": project_id,
                "name": project.name,
                "stage": project.stage,
                "status": "created",
            }

        except Exception as e:
            self.logger.error(f"Failed to start project: {e}")
            await self._emit_error(project_id, str(e))
            raise

    async def process_client_message(
        self,
        project_id: str,
        message: str,
    ) -> dict[str, Any]:
        """
        Process a message from the client (route to Intermediator).

        Args:
            project_id: Project identifier.
            message: Client message.

        Returns:
            Response from the Intermediator.
        """
        # Add message to conversation history
        self.project_manager.add_conversation_message(
            project_id, "user", message
        )

        # Get current project state
        project = self.project_manager.get_project(project_id)
        if not project:
            return {"error": f"Project {project_id} not found"}

        # Get Intermediator agent
        intermediator = self._agents.get("Intermediator")
        if not intermediator:
            # If no Intermediator registered, return a basic response
            response = {
                "message": f"Received your message: {message[:100]}...",
                "project_id": project_id,
                "stage": project.stage,
            }
            self.project_manager.add_conversation_message(
                project_id, "assistant", response["message"]
            )
            return response

        # Route to Intermediator for processing
        try:
            # Create a message object for the intermediator
            from backend.models.schemas import Message

            msg = Message(
                from_agent="client",
                to_agent="Intermediator",
                content=message,
                message_type="request",
            )

            response_msg = await intermediator.process(msg)

            # Store assistant response
            self.project_manager.add_conversation_message(
                project_id, "assistant", response_msg.content
            )

            return {
                "message": response_msg.content,
                "project_id": project_id,
                "stage": project.stage,
            }

        except Exception as e:
            self.logger.error(f"Error processing client message: {e}")
            return {"error": str(e)}

    async def transition_to_planning(
        self,
        project_id: str,
        requirements: ProjectRequirements,
    ) -> dict[str, Any]:
        """
        Transition project to planning phase.

        Args:
            project_id: Project identifier.
            requirements: Confirmed requirements.

        Returns:
            Status of the transition.
        """
        # Confirm requirements
        requirements.confirmed = True
        requirements.confirmed_at = datetime.utcnow()
        self.project_manager.update_requirements(project_id, requirements)

        # Transition through stages
        self.workflow_engine.transition(
            project_id, ProjectStage.REQUIREMENTS_CONFIRMED
        )
        self.workflow_engine.transition(
            project_id, ProjectStage.PLANNING
        )

        # Emit stage change
        await self.event_emitter.emit(
            "stage_changed",
            {
                "project_id": project_id,
                "stage": ProjectStage.PLANNING.value,
                "previous_stage": ProjectStage.REQUIREMENTS_CONFIRMED.value,
            },
            source="orchestrator",
        )

        # Get Planner agent if available
        planner = self._agents.get("Planner")
        if planner:
            try:
                from backend.models.schemas import Message

                msg = Message(
                    from_agent="Orchestrator",
                    to_agent="Planner",
                    content=requirements.clarified_requirements
                    or requirements.original_request,
                    message_type="request",
                )
                await planner.process(msg)
                self.logger.info("Planner created specifications")
            except Exception as e:
                self.logger.error(f"Planner error: {e}")

        return {
            "project_id": project_id,
            "stage": ProjectStage.PLANNING.value,
            "status": "transitioned",
        }

    async def start_development(
        self,
        project_id: str,
        plan: DevelopmentPlan,
    ) -> dict[str, Any]:
        """
        Start development phase with the approved plan.

        Args:
            project_id: Project identifier.
            plan: Approved development plan.

        Returns:
            Status of the development start.
        """
        # Store and approve the plan
        plan.approved = True
        plan.approved_at = datetime.utcnow()
        self.project_manager.update_plan(project_id, plan)

        # Transition stages
        self.workflow_engine.transition(
            project_id, ProjectStage.PLAN_APPROVED
        )
        self.workflow_engine.transition(
            project_id, ProjectStage.DEVELOPMENT
        )

        # Dispatch tasks
        dispatched = self.task_dispatcher.dispatch_plan(project_id, plan)

        # Emit events
        await self.event_emitter.emit(
            "stage_changed",
            {
                "project_id": project_id,
                "stage": ProjectStage.DEVELOPMENT.value,
            },
            source="orchestrator",
        )

        for task in dispatched:
            await self.event_emitter.emit(
                "task_started",
                {
                    "project_id": project_id,
                    "task_id": task.id,
                    "description": task.plan_task.description,
                    "assigned_to": task.plan_task.assigned_to,
                },
                source="orchestrator",
            )

        # Execute tasks in parallel
        async def task_executor(proj_id: str, task: PlanTask) -> dict[str, Any]:
            """Execute a single task using the appropriate agent."""
            agent_name = task.assigned_to
            agent = self._agents.get(agent_name)

            if not agent:
                return {
                    "error": f"Agent {agent_name} not found",
                    "task_id": task.id,
                }

            try:
                from backend.models.schemas import Message

                msg = Message(
                    from_agent="Orchestrator",
                    to_agent=agent_name,
                    content=task.description,
                    message_type="request",
                    metadata={
                        "task_id": task.id,
                        "file_path": task.file_path,
                    },
                )

                response = await agent.process(msg)

                # Emit file generated event if applicable
                if task.file_path:
                    await self.event_emitter.emit(
                        "file_generated",
                        {
                            "project_id": proj_id,
                            "path": task.file_path,
                            "generated_by": agent_name,
                        },
                        source="orchestrator",
                    )

                await self.event_emitter.emit(
                    "task_completed",
                    {
                        "project_id": proj_id,
                        "task_id": task.id,
                        "status": "completed",
                    },
                    source="orchestrator",
                )

                return {
                    "task_id": task.id,
                    "status": "completed",
                    "response": response.content[:500] if response.content else "",
                }

            except Exception as e:
                self.logger.error(f"Task {task.id} failed: {e}")
                return {
                    "task_id": task.id,
                    "status": "failed",
                    "error": str(e),
                }

        # Start parallel execution
        results = await self.task_dispatcher.execute_parallel_tasks(
            project_id, task_executor
        )

        # Check if all tasks completed
        if self.task_dispatcher.is_project_successful(project_id):
            self.workflow_engine.transition(
                project_id, ProjectStage.DEVELOPMENT_COMPLETE
            )
            await self.event_emitter.emit(
                "milestone_reached",
                {
                    "project_id": project_id,
                    "milestone": "development_complete",
                },
                source="orchestrator",
            )

        return {
            "project_id": project_id,
            "stage": self.workflow_engine.get_current_stage(project_id).value,
            "tasks_completed": len(
                self.task_dispatcher.get_completed_tasks(project_id)
            ),
            "tasks_failed": len(self.task_dispatcher.get_failed_tasks(project_id)),
            "results": results,
        }

    async def request_review(self, project_id: str) -> dict[str, Any]:
        """
        Request code review for the project.

        Args:
            project_id: Project identifier.

        Returns:
            Review status and results.
        """
        # Transition to review stage
        success = self.workflow_engine.transition(
            project_id, ProjectStage.REVIEW
        )
        if not success:
            return {"error": "Cannot transition to review stage"}

        await self.event_emitter.emit(
            "stage_changed",
            {
                "project_id": project_id,
                "stage": ProjectStage.REVIEW.value,
            },
            source="orchestrator",
        )

        # Get Reviewer agent
        reviewer = self._agents.get("Reviewer")
        if not reviewer:
            # Auto-approve if no reviewer
            self.logger.info("No Reviewer agent, auto-approving")
            return {
                "project_id": project_id,
                "stage": ProjectStage.REVIEW.value,
                "status": "auto_approved",
            }

        # Get all project files
        files = self.project_manager.get_files(project_id)
        review_results = []

        for file in files:
            try:
                from backend.models.schemas import Message

                msg = Message(
                    from_agent="Orchestrator",
                    to_agent="Reviewer",
                    content=f"Review file: {file.path}\n\n{file.content}",
                    message_type="request",
                )
                response = await reviewer.process(msg)

                # Mark file as reviewed
                self.project_manager.mark_file_reviewed(
                    project_id, file.path, response.content[:500]
                )

                review_results.append({
                    "path": file.path,
                    "reviewed": True,
                    "notes": response.content[:200],
                })

            except Exception as e:
                self.logger.error(f"Review failed for {file.path}: {e}")
                review_results.append({
                    "path": file.path,
                    "reviewed": False,
                    "error": str(e),
                })

        return {
            "project_id": project_id,
            "stage": ProjectStage.REVIEW.value,
            "status": "reviewed",
            "results": review_results,
        }

    async def run_tests(self, project_id: str) -> dict[str, Any]:
        """
        Run tests on the project.

        Args:
            project_id: Project identifier.

        Returns:
            Test results.
        """
        # Transition to testing stage
        success = self.workflow_engine.transition(
            project_id, ProjectStage.TESTING
        )
        if not success:
            return {"error": "Cannot transition to testing stage"}

        await self.event_emitter.emit(
            "stage_changed",
            {
                "project_id": project_id,
                "stage": ProjectStage.TESTING.value,
            },
            source="orchestrator",
        )

        # Get Tester agent
        tester = self._agents.get("Tester")
        if not tester:
            # Auto-pass if no tester
            self.logger.info("No Tester agent, auto-passing tests")
            self.workflow_engine.transition(
                project_id, ProjectStage.READY_FOR_DELIVERY
            )
            return {
                "project_id": project_id,
                "stage": ProjectStage.READY_FOR_DELIVERY.value,
                "status": "auto_passed",
            }

        # Run tests
        try:
            from backend.models.schemas import Message

            project = self.project_manager.get_project(project_id)
            file_list = [f.path for f in (project.files if project else [])]

            msg = Message(
                from_agent="Orchestrator",
                to_agent="Tester",
                content=f"Run tests for project files: {file_list}",
                message_type="request",
            )
            response = await tester.process(msg)

            # Transition to ready for delivery
            self.workflow_engine.transition(
                project_id, ProjectStage.READY_FOR_DELIVERY
            )

            return {
                "project_id": project_id,
                "stage": ProjectStage.READY_FOR_DELIVERY.value,
                "status": "passed",
                "results": response.content[:500],
            }

        except Exception as e:
            self.logger.error(f"Testing failed: {e}")
            return {
                "project_id": project_id,
                "stage": ProjectStage.TESTING.value,
                "status": "failed",
                "error": str(e),
            }

    async def prepare_delivery(self, project_id: str) -> dict[str, Any]:
        """
        Prepare the project for delivery.

        Args:
            project_id: Project identifier.

        Returns:
            Delivery package info.
        """
        project = self.project_manager.get_project(project_id)
        if not project:
            return {"error": f"Project {project_id} not found"}

        # Transition to delivered
        self.workflow_engine.transition(
            project_id, ProjectStage.DELIVERED
        )

        # Emit completion events
        await self.event_emitter.emit(
            "stage_changed",
            {
                "project_id": project_id,
                "stage": ProjectStage.DELIVERED.value,
            },
            source="orchestrator",
        )

        await self.event_emitter.emit(
            "project_completed",
            {
                "project_id": project_id,
                "name": project.name,
                "file_count": len(project.files),
            },
            source="orchestrator",
        )

        return {
            "project_id": project_id,
            "name": project.name,
            "stage": ProjectStage.DELIVERED.value,
            "files": [f.path for f in project.files],
            "status": "delivered",
        }

    async def handle_agent_error(
        self,
        agent_name: str,
        error: str,
        project_id: str | None = None,
    ) -> None:
        """
        Handle an error from an agent.

        Args:
            agent_name: Name of the agent that errored.
            error: Error message.
            project_id: Optional project ID if error is project-specific.
        """
        self.logger.error(f"Agent {agent_name} error: {error}")

        await self.event_emitter.emit(
            "error_occurred",
            {
                "agent_name": agent_name,
                "error": error,
                "project_id": project_id,
            },
            source="orchestrator",
        )

        # Update project status if applicable
        if project_id:
            self.workflow_engine.transition(
                project_id,
                ProjectStage.FAILED,
                f"Agent {agent_name} failed: {error}",
            )
            self.project_manager.set_error(
                project_id, f"Agent {agent_name} failed: {error}"
            )

    async def get_project_status(self, project_id: str) -> dict[str, Any]:
        """
        Get the current status of a project.

        Args:
            project_id: Project identifier.

        Returns:
            Project status information.
        """
        project = self.project_manager.get_project(project_id)
        if not project:
            return {"error": f"Project {project_id} not found"}

        stage = self.workflow_engine.get_current_stage(project_id)
        history = self.workflow_engine.get_stage_history(project_id)
        pending_tasks = self.task_dispatcher.get_pending_tasks(project_id)
        running_tasks = self.task_dispatcher.get_running_tasks(project_id)
        completed_tasks = self.task_dispatcher.get_completed_tasks(project_id)
        failed_tasks = self.task_dispatcher.get_failed_tasks(project_id)

        return {
            "project_id": project_id,
            "name": project.name,
            "stage": stage.value if stage else None,
            "stage_history": history,
            "file_count": len(project.files),
            "files": [f.path for f in project.files],
            "tasks": {
                "pending": len(pending_tasks),
                "running": len(running_tasks),
                "completed": len(completed_tasks),
                "failed": len(failed_tasks),
            },
            "error": project.error,
            "created_at": project.created_at.isoformat(),
            "updated_at": (
                project.updated_at.isoformat() if project.updated_at else None
            ),
        }

    async def _emit_error(self, project_id: str, error: str) -> None:
        """Emit an error event."""
        await self.event_emitter.emit(
            "error_occurred",
            {
                "project_id": project_id,
                "error": error,
            },
            source="orchestrator",
        )

    def get_all_projects(self) -> list[dict[str, Any]]:
        """
        Get all projects.

        Returns:
            List of project summaries.
        """
        summaries = self.project_manager.list_projects()
        return [
            {
                "id": s.id,
                "name": s.name,
                "stage": s.stage,
                "created_at": s.created_at.isoformat(),
                "file_count": s.file_count,
            }
            for s in summaries
        ]
