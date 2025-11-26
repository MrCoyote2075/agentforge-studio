"""
Tests for Agent implementations.

These tests verify that the agents work correctly,
using mocks to avoid actual AI API calls during testing.
"""

from unittest.mock import AsyncMock, patch

import pytest

from backend.agents.base_agent import AgentState, get_provider_manager
from backend.agents.frontend_agent import FrontendAgent
from backend.agents.helper import Helper
from backend.agents.intermediator import Intermediator
from backend.agents.planner import Planner
from backend.models.schemas import ChatMessage


class TestBaseAgent:
    """Tests for the BaseAgent class."""

    def test_get_provider_manager_singleton(self):
        """Test that provider manager is a singleton."""
        import backend.agents.base_agent as base_agent_module

        base_agent_module._provider_manager = None

        settings_path = "backend.core.ai_clients.provider_manager.get_settings"
        with patch(settings_path) as mock_settings:
            mock_settings.return_value.gemini_api_key = ""
            mock_settings.return_value.openai_api_key = ""
            mock_settings.return_value.anthropic_api_key = ""

            manager1 = get_provider_manager()
            manager2 = get_provider_manager()
            assert manager1 is manager2


class TestIntermedator:
    """Tests for the Intermediator agent."""

    def test_initialization(self):
        """Test that Intermediator initializes correctly."""
        intermediator = Intermediator()
        assert intermediator.name == "Intermediator"
        assert intermediator.status == AgentState.IDLE
        assert len(intermediator.conversation_history) == 0

    def test_conversation_history_starts_empty(self):
        """Test that conversation history is initially empty."""
        intermediator = Intermediator()
        assert intermediator.conversation_history == []

    def test_current_project_id_starts_none(self):
        """Test that current project ID is initially None."""
        intermediator = Intermediator()
        assert intermediator.current_project_id is None

    @pytest.mark.asyncio
    async def test_chat_stores_user_message(self):
        """Test that chat stores user messages in history."""
        intermediator = Intermediator()

        with patch.object(
            intermediator, "get_ai_response", new_callable=AsyncMock
        ) as mock_ai:
            mock_ai.return_value = "Hello! How can I help you?"
            await intermediator.chat("Hello")

        assert len(intermediator.conversation_history) == 2
        assert intermediator.conversation_history[0].role == "user"
        assert intermediator.conversation_history[0].content == "Hello"

    @pytest.mark.asyncio
    async def test_chat_stores_assistant_response(self):
        """Test that chat stores assistant responses in history."""
        intermediator = Intermediator()

        with patch.object(
            intermediator, "get_ai_response", new_callable=AsyncMock
        ) as mock_ai:
            mock_ai.return_value = "Hello! How can I help you?"
            await intermediator.chat("Hello")

        assert intermediator.conversation_history[1].role == "assistant"

    @pytest.mark.asyncio
    async def test_chat_sets_project_id(self):
        """Test that chat sets the current project ID."""
        intermediator = Intermediator()

        with patch.object(
            intermediator, "get_ai_response", new_callable=AsyncMock
        ) as mock_ai:
            mock_ai.return_value = "I'll help with your project!"
            await intermediator.chat("Help me", project_id="test-project")

        assert intermediator.current_project_id == "test-project"

    def test_clear_history(self):
        """Test that clear_history clears conversation."""
        intermediator = Intermediator()
        intermediator._conversation_history = [
            ChatMessage(content="test", role="user")
        ]
        intermediator._current_project_id = "test-id"

        intermediator.clear_history()

        assert len(intermediator.conversation_history) == 0
        assert intermediator.current_project_id is None


class TestPlanner:
    """Tests for the Planner agent."""

    def test_initialization(self):
        """Test that Planner initializes correctly."""
        planner = Planner()
        assert planner.name == "Planner"
        assert planner.status == AgentState.IDLE

    @pytest.mark.asyncio
    async def test_create_specification_returns_dict(self):
        """Test that create_specification returns a dictionary."""
        planner = Planner()

        with patch.object(
            planner, "get_ai_response", new_callable=AsyncMock
        ) as mock_ai:
            mock_ai.return_value = (
                '{"project_name": "Test", "technologies": ["HTML"]}'
            )
            specs = await planner.create_specification("Build a website")

        assert isinstance(specs, dict)

    @pytest.mark.asyncio
    async def test_estimate_complexity_returns_metrics(self):
        """Test that estimate_complexity returns complexity metrics."""
        planner = Planner()

        specs = {
            "pages": [{"name": "Home"}, {"name": "About"}],
            "features": [{"name": "Contact Form"}],
        }
        metrics = await planner.estimate_complexity(specs)

        assert "complexity_score" in metrics
        assert "complexity_level" in metrics
        assert "estimated_pages" in metrics


class TestFrontendAgent:
    """Tests for the FrontendAgent."""

    def test_initialization(self):
        """Test that FrontendAgent initializes correctly."""
        frontend = FrontendAgent()
        assert frontend.name == "FrontendAgent"
        assert frontend.status == AgentState.IDLE

    @pytest.mark.asyncio
    async def test_generate_html_returns_string(self):
        """Test that generate_html returns HTML string."""
        frontend = FrontendAgent()

        with patch.object(
            frontend, "generate_code", new_callable=AsyncMock
        ) as mock_code:
            mock_code.return_value = "<html><body>Test</body></html>"
            html = await frontend.generate_html({"description": "Test page"})

        assert isinstance(html, str)
        assert "html" in html.lower()

    @pytest.mark.asyncio
    async def test_generate_css_returns_string(self):
        """Test that generate_css returns CSS string."""
        frontend = FrontendAgent()

        with patch.object(
            frontend, "generate_code", new_callable=AsyncMock
        ) as mock_code:
            mock_code.return_value = "body { color: black; }"
            css = await frontend.generate_css({"description": "Test styles"})

        assert isinstance(css, str)

    @pytest.mark.asyncio
    async def test_get_generated_files(self):
        """Test getting generated files."""
        frontend = FrontendAgent()
        frontend._generated_files = {"test.html": "<html></html>"}

        files = await frontend.get_generated_files()

        assert "test.html" in files
        assert files is not frontend._generated_files  # Should be a copy

    def test_clear_generated_files(self):
        """Test clearing generated files."""
        frontend = FrontendAgent()
        frontend._generated_files = {"test.html": "<html></html>"}
        frontend._component_registry = {"TestComponent": {}}

        frontend.clear_generated_files()

        assert len(frontend._generated_files) == 0
        assert len(frontend._component_registry) == 0


class TestHelper:
    """Tests for the Helper agent."""

    def test_initialization(self):
        """Test that Helper initializes correctly."""
        helper = Helper()
        assert helper.name == "Helper"
        assert helper.status == AgentState.IDLE

    @pytest.mark.asyncio
    async def test_generate_readme_returns_string(self):
        """Test that generate_readme returns README string."""
        helper = Helper()

        with patch.object(
            helper, "get_ai_response", new_callable=AsyncMock
        ) as mock_ai:
            mock_ai.return_value = "# Test Project\n\nDescription"
            project_info = {"name": "Test", "description": "A test"}
            readme = await helper.generate_readme(project_info)

        assert isinstance(readme, str)
        assert "Test" in readme or "#" in readme

    @pytest.mark.asyncio
    async def test_create_gitignore_returns_string(self):
        """Test that create_gitignore returns gitignore content."""
        helper = Helper()

        with patch.object(
            helper, "get_ai_response", new_callable=AsyncMock
        ) as mock_ai:
            mock_ai.return_value = "node_modules/\n.env"
            gitignore = await helper.create_gitignore("node")

        assert isinstance(gitignore, str)

    @pytest.mark.asyncio
    async def test_create_package_json_returns_valid_json(self):
        """Test that create_package_json returns valid JSON."""
        import json

        helper = Helper()
        package_json = await helper.create_package_json({"name": "test-project"})

        # Should be valid JSON
        parsed = json.loads(package_json)
        assert "name" in parsed
        assert parsed["name"] == "test-project"

    @pytest.mark.asyncio
    async def test_get_generated_docs(self):
        """Test getting generated docs."""
        helper = Helper()
        helper._generated_docs = {"README.md": "# Test"}

        docs = await helper.get_generated_docs()

        assert "README.md" in docs
        assert docs is not helper._generated_docs  # Should be a copy

    def test_clear_generated_docs(self):
        """Test clearing generated docs."""
        helper = Helper()
        helper._generated_docs = {"README.md": "# Test"}
        helper._research_cache = {"topic": {}}

        helper.clear_generated_docs()

        assert len(helper._generated_docs) == 0
        assert len(helper._research_cache) == 0


class TestAgentState:
    """Tests for the AgentState enum."""

    def test_all_states_exist(self):
        """Test that all expected states exist."""
        assert AgentState.IDLE == "idle"
        assert AgentState.BUSY == "busy"
        assert AgentState.WAITING == "waiting"
        assert AgentState.ERROR == "error"
        assert AgentState.OFFLINE == "offline"
