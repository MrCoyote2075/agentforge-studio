"""
Tests for Orchestrator, Workflow Engine, and Task Dispatcher.

These tests verify that the orchestration components work correctly,
including project lifecycle management, workflow transitions,
and parallel task execution.
"""

import asyncio
from datetime import datetime

import pytest

from backend.core.orchestrator import Orchestrator
from backend.core.project_manager import ProjectManager
from backend.core.task_dispatcher import (
    DispatchedTaskState,
    TaskDispatcher,
)
from backend.core.workflow_engine import WorkflowEngine
from backend.models.project import (
    DevelopmentPlan,
    GeneratedFile,
    PlanTask,
    Project,
    ProjectRequirements,
    ProjectStage,
    ProjectSummary,
)


class TestProjectModels:
    """Tests for project models."""

    def test_project_stage_enum(self):
        """Test ProjectStage enum values."""
        assert ProjectStage.INITIALIZED.value == "initialized"
        assert ProjectStage.REQUIREMENTS_GATHERING.value == "requirements_gathering"
        assert ProjectStage.DEVELOPMENT.value == "development"
        assert ProjectStage.DELIVERED.value == "delivered"
        assert ProjectStage.FAILED.value == "failed"

    def test_project_requirements_creation(self):
        """Test creating project requirements."""
        req = ProjectRequirements(
            original_request="Build a portfolio website",
            clarified_requirements="Responsive portfolio with 5 sections",
            features=["hero section", "about page", "contact form"],
            constraints=["must be responsive"],
            confirmed=True,
        )
        assert req.original_request == "Build a portfolio website"
        assert len(req.features) == 3
        assert req.confirmed is True

    def test_plan_task_creation(self):
        """Test creating a plan task."""
        task = PlanTask(
            id="task-1",
            description="Create HTML structure",
            assigned_to="FrontendAgent",
            dependencies=["task-0"],
            estimated_complexity="medium",
            file_path="index.html",
        )
        assert task.id == "task-1"
        assert task.assigned_to == "FrontendAgent"
        assert "task-0" in task.dependencies
        assert task.file_path == "index.html"

    def test_development_plan_creation(self):
        """Test creating a development plan."""
        task = PlanTask(
            description="Create HTML",
            assigned_to="FrontendAgent",
        )
        plan = DevelopmentPlan(
            project_name="Portfolio Website",
            description="A responsive portfolio",
            technologies=["HTML5", "CSS3", "JavaScript"],
            file_structure={"root": ["index.html"], "css": ["styles.css"]},
            tasks=[task],
        )
        assert plan.project_name == "Portfolio Website"
        assert len(plan.technologies) == 3
        assert len(plan.tasks) == 1

    def test_generated_file_creation(self):
        """Test creating a generated file."""
        gen_file = GeneratedFile(
            path="index.html",
            content="<!DOCTYPE html>...",
            file_type="html",
            generated_by="FrontendAgent",
        )
        assert gen_file.path == "index.html"
        assert gen_file.file_type == "html"
        assert gen_file.reviewed is False

    def test_project_creation(self):
        """Test creating a project."""
        project = Project(
            id="proj-001",
            name="Portfolio Website",
            description="A responsive portfolio",
        )
        assert project.id == "proj-001"
        assert project.stage == ProjectStage.INITIALIZED
        assert project.files == []

    def test_project_summary_creation(self):
        """Test creating a project summary."""
        summary = ProjectSummary(
            id="proj-001",
            name="Portfolio Website",
            stage=ProjectStage.DEVELOPMENT,
            created_at=datetime.utcnow(),
            file_count=5,
        )
        assert summary.id == "proj-001"
        assert summary.file_count == 5


class TestWorkflowEngine:
    """Tests for the WorkflowEngine class."""

    def test_create_project(self):
        """Test creating a project in the workflow."""
        engine = WorkflowEngine()
        project = engine.create_project("proj-1", "Test Project")

        assert project.id == "proj-1"
        assert project.name == "Test Project"
        assert project.stage == ProjectStage.INITIALIZED

    def test_create_duplicate_project_raises_error(self):
        """Test that creating a duplicate project raises an error."""
        engine = WorkflowEngine()
        engine.create_project("proj-1", "Test Project")

        with pytest.raises(ValueError):
            engine.create_project("proj-1", "Another Project")

    def test_get_project(self):
        """Test getting a project."""
        engine = WorkflowEngine()
        engine.create_project("proj-1", "Test Project")

        project = engine.get_project("proj-1")
        assert project is not None
        assert project.name == "Test Project"

        missing = engine.get_project("proj-2")
        assert missing is None

    def test_can_transition(self):
        """Test checking valid transitions."""
        engine = WorkflowEngine()
        engine.create_project("proj-1", "Test Project")

        # Valid transition
        assert engine.can_transition("proj-1", ProjectStage.REQUIREMENTS_GATHERING)
        assert engine.can_transition("proj-1", ProjectStage.FAILED)

        # Invalid transition
        assert not engine.can_transition("proj-1", ProjectStage.DEVELOPMENT)
        assert not engine.can_transition("proj-1", ProjectStage.DELIVERED)

    def test_transition(self):
        """Test transitioning a project."""
        engine = WorkflowEngine()
        engine.create_project("proj-1", "Test Project")

        # Valid transition
        success = engine.transition("proj-1", ProjectStage.REQUIREMENTS_GATHERING)
        assert success is True
        assert engine.get_current_stage("proj-1") == ProjectStage.REQUIREMENTS_GATHERING

        # Invalid transition
        success = engine.transition("proj-1", ProjectStage.DELIVERED)
        assert success is False

    def test_get_next_stages(self):
        """Test getting valid next stages."""
        engine = WorkflowEngine()
        engine.create_project("proj-1", "Test Project")

        next_stages = engine.get_next_stages("proj-1")
        assert ProjectStage.REQUIREMENTS_GATHERING in next_stages
        assert ProjectStage.FAILED in next_stages
        assert ProjectStage.DEVELOPMENT not in next_stages

    def test_stage_history(self):
        """Test stage transition history."""
        engine = WorkflowEngine()
        engine.create_project("proj-1", "Test Project")
        engine.transition("proj-1", ProjectStage.REQUIREMENTS_GATHERING)
        engine.transition("proj-1", ProjectStage.REQUIREMENTS_CONFIRMED)

        history = engine.get_stage_history("proj-1")
        assert len(history) == 3  # Initial + 2 transitions
        assert history[0]["stage"] == "initialized"
        assert history[1]["stage"] == "requirements_gathering"
        assert history[2]["stage"] == "requirements_confirmed"

    def test_is_terminal(self):
        """Test checking terminal states."""
        engine = WorkflowEngine()
        engine.create_project("proj-1", "Test Project")

        assert not engine.is_terminal("proj-1")

        engine.transition("proj-1", ProjectStage.FAILED)
        assert engine.is_terminal("proj-1")

    def test_get_projects_by_stage(self):
        """Test getting projects by stage."""
        engine = WorkflowEngine()
        engine.create_project("proj-1", "Project 1")
        engine.create_project("proj-2", "Project 2")
        engine.transition("proj-2", ProjectStage.REQUIREMENTS_GATHERING)

        initialized = engine.get_projects_by_stage(ProjectStage.INITIALIZED)
        gathering = engine.get_projects_by_stage(ProjectStage.REQUIREMENTS_GATHERING)

        assert len(initialized) == 1
        assert len(gathering) == 1

    def test_remove_project(self):
        """Test removing a project."""
        engine = WorkflowEngine()
        engine.create_project("proj-1", "Test Project")

        success = engine.remove_project("proj-1")
        assert success is True
        assert engine.get_project("proj-1") is None

        success = engine.remove_project("proj-nonexistent")
        assert success is False

    def test_clear(self):
        """Test clearing all projects."""
        engine = WorkflowEngine()
        engine.create_project("proj-1", "Project 1")
        engine.create_project("proj-2", "Project 2")

        engine.clear()
        assert len(engine.get_all_projects()) == 0


class TestProjectManager:
    """Tests for the ProjectManager class."""

    def test_create_project(self):
        """Test creating a project."""
        manager = ProjectManager()
        project = manager.create_project("Test Project", "A test project")

        assert project.name == "Test Project"
        assert project.description == "A test project"
        assert project.stage == ProjectStage.INITIALIZED

    def test_get_project(self):
        """Test getting a project."""
        manager = ProjectManager()
        project = manager.create_project("Test Project")

        retrieved = manager.get_project(project.id)
        assert retrieved is not None
        assert retrieved.name == "Test Project"

    def test_update_requirements(self):
        """Test updating project requirements."""
        manager = ProjectManager()
        project = manager.create_project("Test Project")

        requirements = ProjectRequirements(
            original_request="Build a website",
            features=["hero", "about"],
        )
        success = manager.update_requirements(project.id, requirements)

        assert success is True
        updated = manager.get_project(project.id)
        assert updated.requirements is not None
        assert updated.requirements.original_request == "Build a website"

    def test_confirm_requirements(self):
        """Test confirming requirements."""
        manager = ProjectManager()
        project = manager.create_project("Test Project")
        requirements = ProjectRequirements(original_request="Build")
        manager.update_requirements(project.id, requirements)

        success = manager.confirm_requirements(project.id)
        assert success is True

        updated = manager.get_project(project.id)
        assert updated.requirements.confirmed is True

    def test_update_plan(self):
        """Test updating development plan."""
        manager = ProjectManager()
        project = manager.create_project("Test Project")

        plan = DevelopmentPlan(
            project_name="Test",
            technologies=["HTML", "CSS"],
        )
        success = manager.update_plan(project.id, plan)

        assert success is True
        updated = manager.get_project(project.id)
        assert updated.plan is not None

    def test_add_file(self):
        """Test adding a generated file."""
        manager = ProjectManager()
        project = manager.create_project("Test Project")

        gen_file = manager.add_file(
            project.id,
            "index.html",
            "<!DOCTYPE html>...",
            generated_by="FrontendAgent",
        )

        assert gen_file is not None
        assert gen_file.path == "index.html"
        assert gen_file.file_type == "html"

    def test_add_file_updates_existing(self):
        """Test that adding a file with same path updates it."""
        manager = ProjectManager()
        project = manager.create_project("Test Project")

        manager.add_file(project.id, "index.html", "Original content")
        manager.add_file(project.id, "index.html", "Updated content")

        files = manager.get_files(project.id)
        assert len(files) == 1
        assert files[0].content == "Updated content"

    def test_get_files(self):
        """Test getting project files."""
        manager = ProjectManager()
        project = manager.create_project("Test Project")
        manager.add_file(project.id, "index.html", "HTML content")
        manager.add_file(project.id, "styles.css", "CSS content")

        files = manager.get_files(project.id)
        assert len(files) == 2

    def test_delete_file(self):
        """Test deleting a file."""
        manager = ProjectManager()
        project = manager.create_project("Test Project")
        manager.add_file(project.id, "index.html", "content")

        success = manager.delete_file(project.id, "index.html")
        assert success is True
        assert len(manager.get_files(project.id)) == 0

    def test_list_projects(self):
        """Test listing all projects."""
        manager = ProjectManager()
        manager.create_project("Project 1")
        manager.create_project("Project 2")

        summaries = manager.list_projects()
        assert len(summaries) == 2

    def test_add_conversation_message(self):
        """Test adding conversation messages."""
        manager = ProjectManager()
        project = manager.create_project("Test Project")

        success = manager.add_conversation_message(
            project.id, "user", "Hello"
        )
        assert success is True

        updated = manager.get_project(project.id)
        assert len(updated.conversation_history) == 1


class TestTaskDispatcher:
    """Tests for the TaskDispatcher class."""

    def test_dispatch_plan(self):
        """Test dispatching a development plan."""
        dispatcher = TaskDispatcher()
        plan = DevelopmentPlan(
            project_name="Test",
            tasks=[
                PlanTask(id="task-1", description="Task 1", assigned_to="Agent1"),
                PlanTask(id="task-2", description="Task 2", assigned_to="Agent2"),
            ],
        )

        dispatched = dispatcher.dispatch_plan("proj-1", plan)
        assert len(dispatched) == 2
        assert all(t.state == DispatchedTaskState.PENDING for t in dispatched)

    @pytest.mark.asyncio
    async def test_execute_parallel_tasks(self):
        """Test parallel task execution."""
        dispatcher = TaskDispatcher()
        plan = DevelopmentPlan(
            project_name="Test",
            tasks=[
                PlanTask(id="task-1", description="Task 1", assigned_to="Agent1"),
                PlanTask(id="task-2", description="Task 2", assigned_to="Agent2"),
            ],
        )
        dispatcher.dispatch_plan("proj-1", plan)

        async def executor(project_id: str, task: PlanTask) -> dict:
            await asyncio.sleep(0.01)  # Simulate work
            return {"task_id": task.id, "status": "done"}

        results = await dispatcher.execute_parallel_tasks("proj-1", executor)

        assert len(results) == 2
        assert dispatcher.is_project_complete("proj-1")
        assert dispatcher.is_project_successful("proj-1")

    @pytest.mark.asyncio
    async def test_task_dependencies(self):
        """Test that task dependencies are respected."""
        dispatcher = TaskDispatcher()
        execution_order = []

        plan = DevelopmentPlan(
            project_name="Test",
            tasks=[
                PlanTask(id="task-1", description="First", assigned_to="Agent1"),
                PlanTask(
                    id="task-2",
                    description="Second",
                    assigned_to="Agent2",
                    dependencies=["task-1"],
                ),
            ],
        )
        dispatcher.dispatch_plan("proj-1", plan)

        async def executor(project_id: str, task: PlanTask) -> dict:
            execution_order.append(task.id)
            await asyncio.sleep(0.01)
            return {"task_id": task.id}

        await dispatcher.execute_parallel_tasks("proj-1", executor)

        # task-1 must complete before task-2
        assert execution_order.index("task-1") < execution_order.index("task-2")

    @pytest.mark.asyncio
    async def test_task_failure_handling(self):
        """Test handling of task failures."""
        dispatcher = TaskDispatcher()
        plan = DevelopmentPlan(
            project_name="Test",
            tasks=[
                PlanTask(id="task-1", description="Will fail", assigned_to="Agent1"),
            ],
        )
        dispatcher.dispatch_plan("proj-1", plan)

        async def executor(project_id: str, task: PlanTask) -> dict:
            raise RuntimeError("Task failed")

        await dispatcher.execute_parallel_tasks("proj-1", executor)

        failed = dispatcher.get_failed_tasks("proj-1")
        assert len(failed) == 1
        assert not dispatcher.is_project_successful("proj-1")

    def test_handle_task_completion(self):
        """Test manually handling task completion."""
        dispatcher = TaskDispatcher()
        plan = DevelopmentPlan(
            project_name="Test",
            tasks=[
                PlanTask(id="task-1", description="Task", assigned_to="Agent1"),
            ],
        )
        dispatcher.dispatch_plan("proj-1", plan)

        success = dispatcher.handle_task_completion(
            "task-1", {"result": "done"}, "proj-1"
        )
        assert success is True

        task = dispatcher.get_task_status("task-1", "proj-1")
        assert task.state == DispatchedTaskState.COMPLETED

    def test_handle_task_failure(self):
        """Test manually handling task failure."""
        dispatcher = TaskDispatcher()
        plan = DevelopmentPlan(
            project_name="Test",
            tasks=[
                PlanTask(id="task-1", description="Task", assigned_to="Agent1"),
            ],
        )
        dispatcher.dispatch_plan("proj-1", plan)

        success = dispatcher.handle_task_failure("task-1", "Error occurred", "proj-1")
        assert success is True

        task = dispatcher.get_task_status("task-1", "proj-1")
        assert task.state == DispatchedTaskState.FAILED
        assert task.error == "Error occurred"

    def test_cancel_task(self):
        """Test canceling a pending task."""
        dispatcher = TaskDispatcher()
        plan = DevelopmentPlan(
            project_name="Test",
            tasks=[
                PlanTask(id="task-1", description="Task", assigned_to="Agent1"),
            ],
        )
        dispatcher.dispatch_plan("proj-1", plan)

        success = dispatcher.cancel_task("task-1", "proj-1")
        assert success is True

        task = dispatcher.get_task_status("task-1", "proj-1")
        assert task.state == DispatchedTaskState.CANCELLED

    def test_get_task_lists(self):
        """Test getting tasks by state."""
        dispatcher = TaskDispatcher()
        plan = DevelopmentPlan(
            project_name="Test",
            tasks=[
                PlanTask(id="task-1", description="Task 1", assigned_to="Agent1"),
                PlanTask(id="task-2", description="Task 2", assigned_to="Agent2"),
                PlanTask(id="task-3", description="Task 3", assigned_to="Agent3"),
            ],
        )
        dispatcher.dispatch_plan("proj-1", plan)

        # Initially all pending
        assert len(dispatcher.get_pending_tasks("proj-1")) == 3

        # Complete one, fail one
        dispatcher.handle_task_completion("task-1", {}, "proj-1")
        dispatcher.handle_task_failure("task-2", "Error", "proj-1")

        assert len(dispatcher.get_pending_tasks("proj-1")) == 1
        assert len(dispatcher.get_completed_tasks("proj-1")) == 1
        assert len(dispatcher.get_failed_tasks("proj-1")) == 1

    def test_clear_project(self):
        """Test clearing tasks for a project."""
        dispatcher = TaskDispatcher()
        plan = DevelopmentPlan(
            project_name="Test",
            tasks=[PlanTask(description="Task", assigned_to="Agent")],
        )
        dispatcher.dispatch_plan("proj-1", plan)

        dispatcher.clear_project("proj-1")
        assert len(dispatcher.get_project_tasks("proj-1")) == 0


class TestOrchestrator:
    """Tests for the Orchestrator class."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test orchestrator initialization."""
        orchestrator = Orchestrator()
        await orchestrator.initialize()

        assert orchestrator._running is True

        await orchestrator.shutdown()
        assert orchestrator._running is False

    @pytest.mark.asyncio
    async def test_start_project(self):
        """Test starting a new project."""
        orchestrator = Orchestrator()
        await orchestrator.initialize()

        result = await orchestrator.start_project("proj-1", "Build a website")

        assert result["project_id"] == "proj-1"
        assert result["status"] == "created"

        # Check project was created
        project = orchestrator.project_manager.get_project("proj-1")
        assert project is not None

        # Check workflow stage
        stage = orchestrator.workflow_engine.get_current_stage("proj-1")
        assert stage == ProjectStage.REQUIREMENTS_GATHERING

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_process_client_message(self):
        """Test processing a client message."""
        orchestrator = Orchestrator()
        await orchestrator.initialize()
        await orchestrator.start_project("proj-1", "Initial request")

        result = await orchestrator.process_client_message(
            "proj-1", "Add more features"
        )

        assert "project_id" in result or "error" not in result

        # Check message was added to history
        project = orchestrator.project_manager.get_project("proj-1")
        # Should have initial message + new message + response
        assert len(project.conversation_history) >= 2

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_transition_to_planning(self):
        """Test transitioning to planning phase."""
        orchestrator = Orchestrator()
        await orchestrator.initialize()
        await orchestrator.start_project("proj-1", "Build a website")

        requirements = ProjectRequirements(
            original_request="Build a website",
            clarified_requirements="Responsive portfolio site",
            features=["hero", "about", "contact"],
        )

        result = await orchestrator.transition_to_planning("proj-1", requirements)

        assert result["stage"] == ProjectStage.PLANNING.value

        # Check requirements were stored
        project = orchestrator.project_manager.get_project("proj-1")
        assert project.requirements.confirmed is True

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_start_development(self):
        """Test starting development phase."""
        orchestrator = Orchestrator()
        await orchestrator.initialize()
        await orchestrator.start_project("proj-1", "Build a website")

        # Transition through stages
        requirements = ProjectRequirements(original_request="Build")
        await orchestrator.transition_to_planning("proj-1", requirements)

        # Create a development plan
        plan = DevelopmentPlan(
            project_name="Test",
            technologies=["HTML", "CSS"],
            tasks=[
                PlanTask(
                    id="task-1",
                    description="Create HTML",
                    assigned_to="FrontendAgent",
                    file_path="index.html",
                ),
            ],
        )

        result = await orchestrator.start_development("proj-1", plan)

        assert "project_id" in result
        assert "tasks_completed" in result

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_get_project_status(self):
        """Test getting project status."""
        orchestrator = Orchestrator()
        await orchestrator.initialize()
        await orchestrator.start_project("proj-1", "Build a website")

        status = await orchestrator.get_project_status("proj-1")

        assert status["project_id"] == "proj-1"
        assert "stage" in status
        assert "tasks" in status
        assert "file_count" in status

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_get_project_status_not_found(self):
        """Test getting status for non-existent project."""
        orchestrator = Orchestrator()
        await orchestrator.initialize()

        status = await orchestrator.get_project_status("nonexistent")
        assert "error" in status

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_register_agent(self):
        """Test registering an agent."""
        orchestrator = Orchestrator()

        class MockAgent:
            pass

        orchestrator.register_agent(
            "TestAgent",
            MockAgent(),
            capabilities=["html", "css"],
        )

        assert "TestAgent" in orchestrator._agents
        agent_info = orchestrator.agent_registry.get_agent("TestAgent")
        assert agent_info is not None

    @pytest.mark.asyncio
    async def test_handle_agent_error(self):
        """Test handling agent errors."""
        orchestrator = Orchestrator()
        await orchestrator.initialize()
        await orchestrator.start_project("proj-1", "Build a website")

        await orchestrator.handle_agent_error(
            "TestAgent", "Something went wrong", "proj-1"
        )

        # Check project is marked as failed
        stage = orchestrator.workflow_engine.get_current_stage("proj-1")
        assert stage == ProjectStage.FAILED

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_get_all_projects(self):
        """Test getting all projects."""
        orchestrator = Orchestrator()
        await orchestrator.initialize()
        await orchestrator.start_project("proj-1", "Project 1")
        await orchestrator.start_project("proj-2", "Project 2")

        projects = orchestrator.get_all_projects()
        assert len(projects) == 2

        await orchestrator.shutdown()


class TestIntegrationWorkflow:
    """Integration tests for the complete workflow."""

    @pytest.mark.asyncio
    async def test_full_project_lifecycle(self):
        """Test a complete project lifecycle."""
        orchestrator = Orchestrator()
        await orchestrator.initialize()

        # Track events
        events = []

        async def event_handler(event):
            events.append(event)

        orchestrator.event_emitter.on("project_created", event_handler)
        orchestrator.event_emitter.on("stage_changed", event_handler)
        orchestrator.event_emitter.on("project_completed", event_handler)

        # 1. Start project
        result = await orchestrator.start_project(
            "proj-1", "Build a simple landing page"
        )
        assert result["status"] == "created"

        # 2. Transition to planning
        requirements = ProjectRequirements(
            original_request="Build a landing page",
            features=["hero section", "call to action"],
        )
        await orchestrator.transition_to_planning("proj-1", requirements)

        # 3. Start development
        plan = DevelopmentPlan(
            project_name="Landing Page",
            technologies=["HTML", "CSS"],
            tasks=[
                PlanTask(
                    id="task-1",
                    description="Create HTML",
                    assigned_to="FrontendAgent",
                    file_path="index.html",
                ),
            ],
        )
        await orchestrator.start_development("proj-1", plan)

        # 4. Request review (auto-approves without Reviewer agent)
        await orchestrator.request_review("proj-1")

        # 5. Run tests (auto-passes without Tester agent)
        await orchestrator.run_tests("proj-1")

        # 6. Prepare delivery
        result = await orchestrator.prepare_delivery("proj-1")
        assert result["status"] == "delivered"

        # Check final stage
        stage = orchestrator.workflow_engine.get_current_stage("proj-1")
        assert stage == ProjectStage.DELIVERED

        # Check events were emitted
        event_types = [e.data.get("project_id") for e in events]
        assert "proj-1" in event_types

        await orchestrator.shutdown()
