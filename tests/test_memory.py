"""
Tests for the Memory System.

These tests verify that the memory system works correctly,
including project memory, application memory, memory manager,
and context builder.
"""

import os
import tempfile

import pytest

from backend.core.memory import (
    ApplicationMemory,
    ContextBuilder,
    MemoryManager,
    ProjectMemory,
)
from backend.models.memory import (
    AgentContext,
    AgentNote,
    BestPractice,
    ClientPreference,
    Decision,
    ErrorRecord,
    Importance,
    MistakeRecord,
    Pattern,
    TaskRecord,
)


class TestMemoryModels:
    """Tests for memory models."""

    def test_importance_enum(self):
        """Test Importance enum values."""
        assert Importance.LOW.value == "low"
        assert Importance.NORMAL.value == "normal"
        assert Importance.HIGH.value == "high"
        assert Importance.CRITICAL.value == "critical"

    def test_client_preference_creation(self):
        """Test creating a client preference."""
        pref = ClientPreference(
            key="theme",
            value="dark",
            importance=Importance.HIGH,
        )
        assert pref.key == "theme"
        assert pref.value == "dark"
        assert pref.importance == Importance.HIGH
        assert pref.recorded_at is not None

    def test_task_record_creation(self):
        """Test creating a task record."""
        task = TaskRecord(
            task_id="task-1",
            summary="Create hero section",
            status="done",
            agent="FrontendAgent",
        )
        assert task.task_id == "task-1"
        assert task.summary == "Create hero section"
        assert task.status == "done"
        assert task.agent == "FrontendAgent"

    def test_error_record_creation(self):
        """Test creating an error record."""
        error = ErrorRecord(
            agent="Reviewer",
            error="Missing alt text on images",
            context={"file": "index.html"},
        )
        assert error.agent == "Reviewer"
        assert error.error == "Missing alt text on images"
        assert error.resolved is False
        assert error.context == {"file": "index.html"}

    def test_agent_note_creation(self):
        """Test creating an agent note."""
        note = AgentNote(
            from_agent="Planner",
            to_agent="FrontendAgent",
            note="Use CSS Grid for layout",
        )
        assert note.from_agent == "Planner"
        assert note.to_agent == "FrontendAgent"
        assert note.note == "Use CSS Grid for layout"

    def test_decision_creation(self):
        """Test creating a decision."""
        decision = Decision(
            decision="Use flexbox for navigation",
            reason="Better browser support",
            made_by="Planner",
        )
        assert decision.decision == "Use flexbox for navigation"
        assert decision.reason == "Better browser support"
        assert decision.made_by == "Planner"

    def test_pattern_creation(self):
        """Test creating a pattern."""
        pattern = Pattern(
            name="Hero Section",
            description="Full-width hero with CTA",
            code_example="<section class='hero'>...</section>",
            category="html",
        )
        assert pattern.name == "Hero Section"
        assert pattern.category == "html"
        assert pattern.times_used == 0

    def test_best_practice_creation(self):
        """Test creating a best practice."""
        practice = BestPractice(
            practice="Always use semantic HTML",
            context="html",
            learned_from="proj-001",
        )
        assert practice.practice == "Always use semantic HTML"
        assert practice.context == "html"
        assert practice.learned_from == "proj-001"

    def test_mistake_record_creation(self):
        """Test creating a mistake record."""
        mistake = MistakeRecord(
            mistake="Fixed heights on text containers",
            consequence="Text overflow on mobile",
            how_to_avoid="Use min-height instead",
            agent="FrontendAgent",
        )
        assert mistake.mistake == "Fixed heights on text containers"
        assert mistake.how_to_avoid == "Use min-height instead"
        assert mistake.occurrences == 1

    def test_agent_context_creation(self):
        """Test creating an agent context."""
        context = AgentContext(
            project_id="proj-1",
            agent_name="FrontendAgent",
            formatted_context="## Project Context",
        )
        assert context.project_id == "proj-1"
        assert context.agent_name == "FrontendAgent"
        assert context.client_preferences == []
        assert context.completed_tasks == []


class TestProjectMemory:
    """Tests for ProjectMemory class."""

    @pytest.fixture
    def project_memory(self):
        """Create a project memory instance."""
        return ProjectMemory("proj-test")

    @pytest.mark.asyncio
    async def test_store_and_get_preferences(self, project_memory):
        """Test storing and retrieving client preferences."""
        await project_memory.store_client_preference(
            "theme", "dark", importance="high"
        )
        await project_memory.store_client_preference(
            "color", "blue", importance="normal"
        )

        prefs = await project_memory.get_client_preferences()
        assert len(prefs) == 2
        assert "theme" in prefs
        assert prefs["theme"].value == "dark"
        assert prefs["theme"].importance == Importance.HIGH

    @pytest.mark.asyncio
    async def test_task_lifecycle(self, project_memory):
        """Test adding and completing tasks."""
        # Add pending task
        await project_memory.add_pending_task({
            "task_id": "task-1",
            "summary": "Create HTML structure",
            "agent": "FrontendAgent",
        })

        pending = await project_memory.get_pending_tasks()
        assert len(pending) == 1
        assert pending[0].summary == "Create HTML structure"

        # Mark as done
        await project_memory.mark_task_done("task-1", "Created HTML structure")

        pending = await project_memory.get_pending_tasks()
        assert len(pending) == 0

        completed = await project_memory.get_completed_tasks()
        assert len(completed) == 1
        assert completed[0].task_id == "task-1"

    @pytest.mark.asyncio
    async def test_upcoming_tasks(self, project_memory):
        """Test adding upcoming tasks."""
        await project_memory.add_upcoming_task({
            "task_id": "task-future",
            "summary": "Add contact form",
            "agent": "FrontendAgent",
        })

        upcoming = await project_memory.get_upcoming_tasks()
        assert len(upcoming) == 1
        assert upcoming[0].summary == "Add contact form"

    @pytest.mark.asyncio
    async def test_error_tracking(self, project_memory):
        """Test logging and resolving errors."""
        error_id = await project_memory.log_error(
            agent="Reviewer",
            error="Missing alt text",
            context={"file": "index.html"},
        )

        unresolved = await project_memory.get_unresolved_errors()
        assert len(unresolved) == 1
        assert unresolved[0].error == "Missing alt text"

        # Resolve error
        await project_memory.mark_error_resolved(
            error_id, "Added alt text to all images"
        )

        unresolved = await project_memory.get_unresolved_errors()
        assert len(unresolved) == 0

    @pytest.mark.asyncio
    async def test_agent_notes(self, project_memory):
        """Test agent notes."""
        await project_memory.add_agent_note(
            agent="Planner",
            note="Use CSS Grid for layout",
        )
        await project_memory.add_targeted_note(
            from_agent="Reviewer",
            to_agent="FrontendAgent",
            note="Fix button colors",
        )

        # Get all notes
        all_notes = await project_memory.get_agent_notes()
        assert len(all_notes) == 2

        # Get notes for specific agent
        frontend_notes = await project_memory.get_agent_notes(
            for_agent="FrontendAgent"
        )
        assert len(frontend_notes) == 2  # Includes broadcast note

        # Notes for Planner shouldn't include targeted note
        planner_notes = await project_memory.get_agent_notes(for_agent="Planner")
        assert len(planner_notes) == 1

    @pytest.mark.asyncio
    async def test_decisions(self, project_memory):
        """Test recording decisions."""
        await project_memory.record_decision(
            decision="Use flexbox for navigation",
            reason="Better browser support",
            made_by="Planner",
        )

        decisions = await project_memory.get_decisions()
        assert len(decisions) == 1
        assert decisions[0].decision == "Use flexbox for navigation"

    @pytest.mark.asyncio
    async def test_get_context_for_agent(self, project_memory):
        """Test getting full context for an agent."""
        await project_memory.store_client_preference("theme", "dark")
        await project_memory.add_pending_task({
            "task_id": "task-1",
            "summary": "Create header",
        })

        context = await project_memory.get_context_for_agent("FrontendAgent")

        assert context["project_id"] == "proj-test"
        assert context["agent_name"] == "FrontendAgent"
        assert len(context["preferences"]) == 1
        assert len(context["pending_tasks"]) == 1

    @pytest.mark.asyncio
    async def test_clear(self, project_memory):
        """Test clearing project memory."""
        await project_memory.store_client_preference("theme", "dark")
        await project_memory.add_pending_task({
            "task_id": "task-1",
            "summary": "Test",
        })

        await project_memory.clear()

        prefs = await project_memory.get_client_preferences()
        pending = await project_memory.get_pending_tasks()

        assert len(prefs) == 0
        assert len(pending) == 0


class TestApplicationMemory:
    """Tests for ApplicationMemory class."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield os.path.join(tmpdir, "test_app_memory.db")

    @pytest.fixture
    async def app_memory(self, temp_db_path):
        """Create an initialized application memory."""
        memory = ApplicationMemory(temp_db_path)
        await memory.initialize()
        return memory

    @pytest.mark.asyncio
    async def test_initialize(self, temp_db_path):
        """Test database initialization."""
        memory = ApplicationMemory(temp_db_path)
        await memory.initialize()

        # Verify database file was created
        assert os.path.exists(temp_db_path)

    @pytest.mark.asyncio
    async def test_store_and_get_patterns(self, app_memory):
        """Test storing and retrieving patterns."""
        await app_memory.store_pattern(
            name="Hero Section",
            description="Full-width hero with CTA",
            code_example="<section class='hero'>...</section>",
            category="html",
        )

        patterns = await app_memory.get_patterns()
        assert len(patterns) == 1
        assert patterns[0].name == "Hero Section"
        assert patterns[0].category == "html"

        # Get by category
        html_patterns = await app_memory.get_patterns(category="html")
        assert len(html_patterns) == 1

        css_patterns = await app_memory.get_patterns(category="css")
        assert len(css_patterns) == 0

    @pytest.mark.asyncio
    async def test_search_patterns(self, app_memory):
        """Test searching patterns."""
        await app_memory.store_pattern(
            name="Hero Section",
            description="Full-width hero",
            code_example="",
            category="html",
        )
        await app_memory.store_pattern(
            name="Navigation Bar",
            description="Responsive nav",
            code_example="",
            category="html",
        )

        results = await app_memory.search_patterns("hero")
        assert len(results) == 1
        assert results[0].name == "Hero Section"

    @pytest.mark.asyncio
    async def test_increment_pattern_usage(self, app_memory):
        """Test incrementing pattern usage."""
        pattern_id = await app_memory.store_pattern(
            name="Test Pattern",
            description="Test",
            code_example="",
            category="test",
        )

        await app_memory.increment_pattern_usage(pattern_id)
        await app_memory.increment_pattern_usage(pattern_id)

        patterns = await app_memory.get_patterns()
        assert patterns[0].times_used == 2

    @pytest.mark.asyncio
    async def test_store_and_get_best_practices(self, app_memory):
        """Test storing and retrieving best practices."""
        await app_memory.store_best_practice(
            practice="Always use semantic HTML",
            context="html",
            learned_from="proj-001",
        )

        practices = await app_memory.get_best_practices()
        assert len(practices) == 1
        assert practices[0].practice == "Always use semantic HTML"

        # Get by context
        html_practices = await app_memory.get_best_practices(context="html")
        assert len(html_practices) == 1

    @pytest.mark.asyncio
    async def test_store_and_get_mistakes(self, app_memory):
        """Test storing and retrieving mistakes."""
        await app_memory.store_mistake(
            mistake="Fixed heights on text",
            consequence="Text overflow",
            how_to_avoid="Use min-height",
            agent="FrontendAgent",
        )

        mistakes = await app_memory.get_mistakes_for_agent("FrontendAgent")
        assert len(mistakes) == 1
        assert mistakes[0].mistake == "Fixed heights on text"

    @pytest.mark.asyncio
    async def test_duplicate_mistake_increments_count(self, app_memory):
        """Test that storing same mistake increments occurrence count."""
        await app_memory.store_mistake(
            mistake="Fixed heights on text",
            consequence="Text overflow",
            how_to_avoid="Use min-height",
            agent="FrontendAgent",
        )
        await app_memory.store_mistake(
            mistake="Fixed heights on text",
            consequence="Text overflow",
            how_to_avoid="Use min-height",
            agent="FrontendAgent",
        )

        mistakes = await app_memory.get_mistakes_for_agent("FrontendAgent")
        assert len(mistakes) == 1
        assert mistakes[0].occurrences == 2

    @pytest.mark.asyncio
    async def test_learn_from_feedback(self, app_memory):
        """Test storing feedback for learning."""
        learning_id = await app_memory.learn_from_feedback(
            project_id="proj-001",
            feedback="Great work on the responsive design!",
            rating=5,
        )

        assert learning_id is not None

    @pytest.mark.asyncio
    async def test_get_learnings_for_task(self, app_memory):
        """Test getting learnings for a task type."""
        # Add some patterns and practices
        await app_memory.store_pattern(
            name="HTML Pattern",
            description="HTML pattern",
            code_example="",
            category="html",
        )
        await app_memory.store_best_practice(
            practice="Use semantic HTML",
            context="html",
            learned_from="manual",
        )

        learnings = await app_memory.get_learnings_for_task("html")

        assert "patterns" in learnings
        assert "best_practices" in learnings
        assert "mistakes_to_avoid" in learnings


class TestMemoryManager:
    """Tests for MemoryManager class."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield os.path.join(tmpdir, "test_memory.db")

    @pytest.fixture
    async def memory_manager(self, temp_db_path):
        """Create an initialized memory manager."""
        manager = MemoryManager(db_path=temp_db_path)
        await manager.initialize()
        return manager

    @pytest.mark.asyncio
    async def test_initialize(self, temp_db_path):
        """Test memory manager initialization."""
        manager = MemoryManager(db_path=temp_db_path)
        await manager.initialize()
        assert manager._initialized is True

    @pytest.mark.asyncio
    async def test_get_project_memory(self, memory_manager):
        """Test getting project memory."""
        mem = memory_manager.get_project_memory("proj-1")
        assert mem is not None
        assert mem.project_id == "proj-1"

        # Getting same project returns same instance
        mem2 = memory_manager.get_project_memory("proj-1")
        assert mem is mem2

    @pytest.mark.asyncio
    async def test_clear_project_memory(self, memory_manager):
        """Test clearing project memory."""
        mem = memory_manager.get_project_memory("proj-1")
        await mem.store_client_preference("test", "value")

        await memory_manager.clear_project_memory("proj-1")

        assert not memory_manager.has_project_memory("proj-1")

    @pytest.mark.asyncio
    async def test_build_agent_context(self, memory_manager):
        """Test building agent context."""
        # Add some project data
        await memory_manager.store_preference("proj-1", "theme", "dark")
        await memory_manager.add_note(
            "proj-1", "Planner", "Use Grid layout"
        )

        context = await memory_manager.build_agent_context(
            "proj-1", "FrontendAgent"
        )

        assert isinstance(context, AgentContext)
        assert context.project_id == "proj-1"
        assert context.agent_name == "FrontendAgent"
        assert len(context.client_preferences) == 1
        assert context.formatted_context != ""

    @pytest.mark.asyncio
    async def test_convenience_methods(self, memory_manager):
        """Test convenience methods for quick access."""
        # Store preference
        await memory_manager.store_preference(
            "proj-1", "color", "blue", "high"
        )

        # Log error
        error_id = await memory_manager.log_error(
            "proj-1", "Reviewer", "Missing alt text", {"file": "index.html"}
        )
        assert error_id is not None

        # Add note
        await memory_manager.add_note(
            "proj-1", "Planner", "Use flexbox"
        )

        # Record decision
        await memory_manager.record_decision(
            "proj-1", "Use Grid", "Better layout", "Planner"
        )

        # Verify data was stored
        context = await memory_manager.build_agent_context(
            "proj-1", "FrontendAgent"
        )
        assert len(context.client_preferences) == 1
        assert len(context.unresolved_errors) == 1
        assert len(context.agent_notes) == 1
        assert len(context.decisions) == 1

    @pytest.mark.asyncio
    async def test_get_formatted_context(self, memory_manager):
        """Test getting formatted context string."""
        await memory_manager.store_preference("proj-1", "theme", "dark")

        formatted = await memory_manager.get_formatted_context(
            "proj-1", "FrontendAgent"
        )

        assert isinstance(formatted, str)
        assert "Project Context" in formatted
        assert "theme" in formatted

    @pytest.mark.asyncio
    async def test_extract_learnings(self, memory_manager):
        """Test extracting learnings from a project."""
        # Add some decisions to extract from
        await memory_manager.record_decision(
            "proj-1",
            "Always use semantic HTML for better accessibility",
            "Improves SEO and screen reader support",
            "Planner",
        )

        await memory_manager.extract_learnings("proj-1")

        # Check best practices were stored
        practices = await memory_manager.app_memory.get_best_practices()
        assert len(practices) >= 1


class TestContextBuilder:
    """Tests for ContextBuilder class."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield os.path.join(tmpdir, "test_context.db")

    @pytest.fixture
    async def context_builder(self, temp_db_path):
        """Create a context builder with initialized memory manager."""
        manager = MemoryManager(db_path=temp_db_path)
        await manager.initialize()
        return ContextBuilder(manager)

    @pytest.mark.asyncio
    async def test_build_context(self, context_builder):
        """Test building full context."""
        # Add some data
        await context_builder.memory_manager.store_preference(
            "proj-1", "theme", "dark"
        )
        await context_builder.memory_manager.add_note(
            "proj-1", "Planner", "Use Grid"
        )

        context = await context_builder.build_context(
            "proj-1", "FrontendAgent"
        )

        assert isinstance(context, str)
        assert "Project Context" in context

    @pytest.mark.asyncio
    async def test_build_minimal_context(self, context_builder):
        """Test building minimal context."""
        await context_builder.memory_manager.store_preference(
            "proj-1", "theme", "dark"
        )

        context = await context_builder.build_minimal_context(
            "proj-1", "FrontendAgent"
        )

        assert isinstance(context, str)
        assert "FrontendAgent" in context

    @pytest.mark.asyncio
    async def test_build_task_focused_context(self, context_builder):
        """Test building task-focused context."""
        await context_builder.memory_manager.store_preference(
            "proj-1", "html_style", "semantic"
        )

        context = await context_builder.build_task_focused_context(
            "proj-1", "FrontendAgent", "html"
        )

        assert isinstance(context, str)
        assert "HTML" in context

    @pytest.mark.asyncio
    async def test_build_review_context(self, context_builder):
        """Test building review context."""
        project_mem = context_builder.memory_manager.get_project_memory("proj-1")
        await project_mem.mark_task_done("task-1", "Created hero section")

        context = await context_builder.build_review_context("proj-1")

        assert isinstance(context, str)
        assert "Review" in context

    @pytest.mark.asyncio
    async def test_build_handoff_context(self, context_builder):
        """Test building handoff context."""
        project_mem = context_builder.memory_manager.get_project_memory("proj-1")
        await project_mem.add_targeted_note(
            "Planner", "FrontendAgent", "Use flexbox for nav"
        )

        context = await context_builder.build_handoff_context(
            "proj-1", "Planner", "FrontendAgent"
        )

        assert isinstance(context, str)
        assert "Handoff" in context
        assert "Planner" in context
        assert "FrontendAgent" in context


class TestMemoryIntegration:
    """Integration tests for the complete memory system."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield os.path.join(tmpdir, "test_integration.db")

    @pytest.mark.asyncio
    async def test_full_project_workflow(self, temp_db_path):
        """Test a complete project workflow with memory."""
        manager = MemoryManager(db_path=temp_db_path)
        await manager.initialize()

        project_id = "proj-integration"

        # 1. Store client preferences
        await manager.store_preference(
            project_id, "design_style", "modern", "high"
        )
        await manager.store_preference(
            project_id, "color_scheme", "blue and white", "normal"
        )

        # 2. Record planning decisions
        await manager.record_decision(
            project_id,
            "Use CSS Grid for page layout",
            "Modern approach with good support",
            "Planner",
        )

        # 3. Add tasks
        project_mem = manager.get_project_memory(project_id)
        await project_mem.add_pending_task({
            "task_id": "task-1",
            "summary": "Create HTML structure",
            "agent": "FrontendAgent",
        })
        await project_mem.add_upcoming_task({
            "task_id": "task-2",
            "summary": "Add styling",
            "agent": "FrontendAgent",
        })

        # 4. Leave notes for other agents
        await manager.add_note(
            project_id, "Planner", "Remember to use semantic HTML"
        )

        # 5. Complete a task
        await project_mem.mark_task_done(
            "task-1", "Created HTML structure with semantic elements"
        )

        # 6. Log an error
        await manager.log_error(
            project_id,
            "Reviewer",
            "Missing viewport meta tag",
            {"severity": "medium"},
        )

        # 7. Build context for agent
        context = await manager.build_agent_context(
            project_id, "FrontendAgent"
        )

        # Verify context contains all data
        assert len(context.client_preferences) == 2
        assert len(context.completed_tasks) == 1
        assert len(context.upcoming_tasks) == 1
        assert len(context.unresolved_errors) == 1
        assert len(context.agent_notes) == 1
        assert len(context.decisions) == 1

        # Verify formatted context
        formatted = context.formatted_context
        assert "design_style" in formatted
        assert "CSS Grid" in formatted
        assert "semantic HTML" in formatted
        assert "viewport meta tag" in formatted

        # 8. Extract learnings (simulating project completion)
        await manager.extract_learnings(project_id, "Great responsive design!")

        # 9. Clear project memory
        await manager.clear_project_memory(project_id)
        assert not manager.has_project_memory(project_id)

        # 10. Application memory persists
        practices = await manager.app_memory.get_best_practices()
        assert len(practices) >= 1  # At least the decision was stored

        await manager.close()

    @pytest.mark.asyncio
    async def test_memory_persistence(self, temp_db_path):
        """Test that application memory persists across instances."""
        # First instance - store data
        manager1 = MemoryManager(db_path=temp_db_path)
        await manager1.initialize()

        await manager1.app_memory.store_pattern(
            name="Persistent Pattern",
            description="This should persist",
            code_example="<div>Test</div>",
            category="test",
        )
        await manager1.close()

        # Second instance - verify data persists
        manager2 = MemoryManager(db_path=temp_db_path)
        await manager2.initialize()

        patterns = await manager2.app_memory.get_patterns()
        assert len(patterns) == 1
        assert patterns[0].name == "Persistent Pattern"

        await manager2.close()
