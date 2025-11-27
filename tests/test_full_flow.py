"""
Tests for the Full Website Generation Flow.

These tests verify the complete end-to-end flow from user message
to generated website files.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from backend.agents.frontend_agent import FrontendAgent
from backend.agents.intermediator import Intermediator
from backend.agents.planner import Planner
from backend.agents.reviewer import Reviewer
from backend.core.flow_controller import FlowController, FlowStage
from backend.core.orchestrator import Orchestrator
from backend.core.workspace_manager import WorkspaceManager


class TestFlowController:
    """Tests for the FlowController class."""

    def test_initialization(self):
        """Test that FlowController initializes correctly."""
        controller = FlowController()
        assert controller.orchestrator is not None
        assert controller.memory_manager is not None
        assert controller.workspace_manager is not None
        assert controller.current_stage == {}
        assert controller.requirements == {}

    def test_get_stage_default(self):
        """Test that get_stage returns default stage for new project."""
        controller = FlowController()
        stage = controller.get_stage("new-project")
        assert stage == FlowStage.GATHERING_REQUIREMENTS

    def test_is_confirmation(self):
        """Test confirmation detection."""
        controller = FlowController()

        # Should detect confirmations
        assert controller._is_confirmation("yes") is True
        assert controller._is_confirmation("Yes, let's do it") is True
        assert controller._is_confirmation("ok") is True
        assert controller._is_confirmation("Sure, go ahead") is True
        assert controller._is_confirmation("sounds good") is True
        assert controller._is_confirmation("perfect") is True
        assert controller._is_confirmation("build it") is True

        # Should not detect non-confirmations
        assert controller._is_confirmation("hello") is False
        assert controller._is_confirmation("I want a website") is False
        assert controller._is_confirmation("no") is False

    def test_create_default_plan(self):
        """Test default plan creation."""
        controller = FlowController()
        requirements = {
            "website_type": "portfolio",
            "pages": ["Home", "About"],
            "features": ["contact form"],
        }

        plan = controller._create_default_plan(requirements)

        assert "tasks" in plan
        assert "file_structure" in plan
        assert "estimated_time" in plan
        assert len(plan["tasks"]) == 3  # HTML, CSS, JS
        assert "index.html" in plan["file_structure"]
        assert "css/styles.css" in plan["file_structure"]
        assert "js/script.js" in plan["file_structure"]

    @pytest.mark.asyncio
    async def test_trigger_planning(self):
        """Test planning trigger."""
        controller = FlowController()
        requirements = {
            "website_type": "portfolio",
            "pages": ["Home", "About"],
        }

        plan = await controller.trigger_planning("proj-1", requirements)

        assert controller.current_stage["proj-1"] == FlowStage.PLANNING
        assert "tasks" in plan
        assert "file_structure" in plan
        assert controller.plans["proj-1"] == plan

    @pytest.mark.asyncio
    async def test_generate_default_files(self):
        """Test default file generation."""
        controller = FlowController()
        plan = {
            "tasks": [
                {"id": "1", "type": "html", "file": "index.html"},
            ],
        }
        requirements = {
            "website_type": "landing",
            "title": "My Website",
            "description": "A great website",
        }

        files = await controller._generate_default_files(plan, requirements)

        assert len(files) == 3
        file_paths = [f["path"] for f in files]
        assert "index.html" in file_paths
        assert "css/styles.css" in file_paths
        assert "js/script.js" in file_paths

        # Check HTML content includes title
        html_file = next(f for f in files if f["path"] == "index.html")
        assert "My Website" in html_file["content"]

    @pytest.mark.asyncio
    async def test_trigger_development(self):
        """Test development trigger."""
        controller = FlowController()
        controller.requirements["proj-1"] = {"website_type": "portfolio"}
        plan = {
            "tasks": [{"id": "1", "type": "html", "file": "index.html"}],
        }

        files = await controller.trigger_development("proj-1", plan)

        assert controller.current_stage["proj-1"] == FlowStage.DEVELOPMENT
        assert len(files) > 0
        assert controller.generated_files["proj-1"] == files

    @pytest.mark.asyncio
    async def test_trigger_review(self):
        """Test review trigger."""
        controller = FlowController()
        files = [
            {"path": "index.html", "content": "<html></html>", "type": "html"},
        ]

        result = await controller.trigger_review("proj-1", files)

        assert controller.current_stage["proj-1"] == FlowStage.COMPLETE
        assert "status" in result
        assert result["status"] == "reviewed"

    @pytest.mark.asyncio
    async def test_process_user_message_without_confirmation(self):
        """Test processing message that is not a confirmation."""
        controller = FlowController()

        # Create mock intermediator
        mock_intermediator = MagicMock()
        mock_intermediator.chat = AsyncMock(return_value="What would you like to build?")
        mock_intermediator.conversation_history = []

        result = await controller.process_user_message(
            "proj-1",
            "I want to build a website",
            mock_intermediator,
        )

        assert result["stage"] == FlowStage.GATHERING_REQUIREMENTS.value
        assert "response" in result
        assert result["files_generated"] is False

    @pytest.mark.asyncio
    async def test_get_generated_files(self):
        """Test getting generated files."""
        controller = FlowController()
        controller.generated_files["proj-1"] = [
            {"path": "index.html", "content": "<html></html>", "type": "html"},
        ]

        files = controller.get_generated_files("proj-1")
        assert len(files) == 1
        assert files[0]["path"] == "index.html"

    @pytest.mark.asyncio
    async def test_get_plan(self):
        """Test getting plan."""
        controller = FlowController()
        controller.plans["proj-1"] = {"tasks": []}

        plan = controller.get_plan("proj-1")
        assert plan is not None
        assert "tasks" in plan

        # Non-existent project
        assert controller.get_plan("nonexistent") is None


class TestIntermedatorRequirementsDetection:
    """Tests for Intermediator requirements completion detection."""

    def test_is_confirmation(self):
        """Test confirmation detection in Intermediator."""
        intermediator = Intermediator()

        assert intermediator._is_confirmation("yes") is True
        assert intermediator._is_confirmation("Yes please") is True
        assert intermediator._is_confirmation("go ahead") is True
        assert intermediator._is_confirmation("build it") is True

        assert intermediator._is_confirmation("hello") is False
        assert intermediator._is_confirmation("what?") is False

    def test_analyze_conversation_for_requirements(self):
        """Test requirements extraction from conversation."""
        from backend.models.schemas import ChatMessage

        intermediator = Intermediator()

        # Add some conversation history
        intermediator._conversation_history = [
            ChatMessage(content="I want a portfolio website", role="user"),
            ChatMessage(content="Great! What pages do you need?", role="assistant"),
            ChatMessage(content="Home, About, and Contact pages", role="user"),
            ChatMessage(content="Should I add a contact form?", role="assistant"),
            ChatMessage(content="Yes, with a contact form", role="user"),
        ]

        requirements = intermediator._analyze_conversation_for_requirements()

        assert requirements["website_type"] == "portfolio"
        assert "About" in requirements["pages"]
        assert "Contact" in requirements["pages"]
        assert "contact form" in requirements["features"]


class TestFrontendAgentWebsiteGeneration:
    """Tests for FrontendAgent website generation methods."""

    @pytest.mark.asyncio
    async def test_generate_file_html(self):
        """Test generating HTML file."""
        frontend = FrontendAgent()

        with patch.object(
            frontend, "generate_html", new_callable=AsyncMock
        ) as mock_html:
            mock_html.return_value = "<html><body>Test</body></html>"

            task = {"id": "1", "type": "html", "file": "index.html", "description": "Main page"}
            requirements = {"description": "A portfolio website"}

            result = await frontend.generate_file(task, requirements)

            assert result["path"] == "index.html"
            assert result["type"] == "html"
            assert "html" in result["content"].lower()

    @pytest.mark.asyncio
    async def test_generate_file_css(self):
        """Test generating CSS file."""
        frontend = FrontendAgent()

        with patch.object(
            frontend, "generate_css", new_callable=AsyncMock
        ) as mock_css:
            mock_css.return_value = "body { color: black; }"

            task = {"id": "2", "type": "css", "file": "styles.css", "description": "Styles"}
            requirements = {}

            result = await frontend.generate_file(task, requirements)

            assert result["path"] == "styles.css"
            assert result["type"] == "css"

    @pytest.mark.asyncio
    async def test_generate_website(self):
        """Test generating entire website."""
        frontend = FrontendAgent()

        with patch.object(
            frontend, "generate_file", new_callable=AsyncMock
        ) as mock_gen:
            mock_gen.side_effect = [
                {"path": "index.html", "content": "<html></html>", "type": "html"},
                {"path": "styles.css", "content": "body {}", "type": "css"},
            ]

            plan = {
                "tasks": [
                    {"id": "1", "type": "html", "file": "index.html"},
                    {"id": "2", "type": "css", "file": "styles.css"},
                ],
            }
            requirements = {}

            files = await frontend.generate_website(plan, requirements)

            assert len(files) == 2
            assert mock_gen.call_count == 2


class TestPlannerCreatePlan:
    """Tests for Planner create_plan method."""

    @pytest.mark.asyncio
    async def test_create_plan_returns_structured_output(self):
        """Test that create_plan returns properly structured output."""
        planner = Planner()

        with patch.object(
            planner, "create_specification", new_callable=AsyncMock
        ) as mock_spec:
            mock_spec.return_value = {
                "project_name": "Test",
                "file_structure": {
                    "root": ["index.html"],
                    "css": ["styles.css"],
                },
                "tasks": [
                    {
                        "id": "task-1",
                        "description": "Create HTML",
                        "assigned_to": "FrontendAgent",
                        "file_path": "index.html",
                    },
                ],
            }

            requirements = {"website_type": "portfolio"}
            plan = await planner.create_plan(requirements)

            assert "tasks" in plan
            assert "file_structure" in plan
            assert "estimated_time" in plan
            assert len(plan["tasks"]) >= 1

    def test_get_file_type(self):
        """Test file type detection."""
        planner = Planner()

        assert planner._get_file_type("index.html") == "html"
        assert planner._get_file_type("styles.css") == "css"
        assert planner._get_file_type("script.js") == "js"
        assert planner._get_file_type("readme.md") == "other"


class TestFullFlowIntegration:
    """Integration tests for the complete flow."""

    @pytest.mark.asyncio
    async def test_complete_flow_simulation(self):
        """Test simulating a complete flow."""
        controller = FlowController()

        # Simulate a project going through all stages
        project_id = "test-proj-1"

        # Start with requirements
        requirements = {
            "website_type": "landing",
            "pages": ["Home"],
            "features": ["responsive design"],
            "title": "Test Site",
            "description": "A test landing page",
        }
        controller.requirements[project_id] = requirements

        # Trigger planning
        plan = await controller.trigger_planning(project_id, requirements)
        assert controller.current_stage[project_id] == FlowStage.PLANNING
        assert "tasks" in plan

        # Trigger development
        files = await controller.trigger_development(project_id, plan)
        assert controller.current_stage[project_id] == FlowStage.DEVELOPMENT
        assert len(files) > 0

        # Trigger review
        review_result = await controller.trigger_review(project_id, files)
        assert controller.current_stage[project_id] == FlowStage.COMPLETE
        assert review_result["status"] == "reviewed"

        # Check final state
        assert len(controller.generated_files[project_id]) > 0

    @pytest.mark.asyncio
    async def test_flow_with_mocked_agents(self):
        """Test flow with mocked agents in orchestrator."""
        orchestrator = Orchestrator()

        # Create mock agents
        mock_planner = MagicMock()
        mock_planner.create_specification = AsyncMock(return_value={
            "project_name": "Test",
            "tasks": [],
            "file_structure": {},
        })

        mock_frontend = MagicMock()
        mock_frontend.generate_html = AsyncMock(return_value="<html></html>")
        mock_frontend.generate_css = AsyncMock(return_value="body {}")
        mock_frontend.generate_javascript = AsyncMock(return_value="console.log('test');")

        mock_reviewer = MagicMock()
        mock_reviewer.review_code = AsyncMock(return_value=[])

        # Register mock agents
        orchestrator.register_agent("Planner", mock_planner, ["planning"])
        orchestrator.register_agent("FrontendAgent", mock_frontend, ["html", "css", "js"])
        orchestrator.register_agent("Reviewer", mock_reviewer, ["review"])

        # Create controller with the orchestrator
        controller = FlowController(orchestrator=orchestrator)

        # Run flow
        requirements = {"website_type": "test"}
        plan = await controller.trigger_planning("proj-1", requirements)
        files = await controller.trigger_development("proj-1", plan)

        # Verify files were generated
        assert len(files) > 0


class TestFlowStageEnum:
    """Tests for FlowStage enum."""

    def test_all_stages_exist(self):
        """Test that all expected stages exist."""
        assert FlowStage.GATHERING_REQUIREMENTS.value == "gathering_requirements"
        assert FlowStage.REQUIREMENTS_CONFIRMED.value == "requirements_confirmed"
        assert FlowStage.PLANNING.value == "planning"
        assert FlowStage.DEVELOPMENT.value == "development"
        assert FlowStage.REVIEW.value == "review"
        assert FlowStage.COMPLETE.value == "complete"
        assert FlowStage.FAILED.value == "failed"
