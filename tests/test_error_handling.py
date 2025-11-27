"""
Tests for Error Handling System.

These tests verify that the error handling components work correctly,
including loop detection, timeout handling, crash recovery,
error recovery strategies, and graceful degradation.
"""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from backend.core.crash_recovery import CrashRecovery
from backend.core.error_recovery import (
    ErrorRecovery,
    ErrorType,
    RecoveryAction,
)
from backend.core.graceful_degradation import (
    DegradationAction,
    DegradationLevel,
    GracefulDegradation,
)
from backend.core.loop_detector import LoopDetector
from backend.core.timeout_manager import TimeoutError, TimeoutManager


class TestLoopDetector:
    """Tests for the LoopDetector class."""

    def test_initialization(self):
        """Test LoopDetector initialization."""
        detector = LoopDetector(max_retries=5)
        assert detector.max_retries == 5
        assert len(detector.get_failed_tasks()) == 0

    def test_record_attempt_increments_count(self):
        """Test that recording attempts increments the counter."""
        detector = LoopDetector(max_retries=3)

        count1 = detector.record_attempt("task-1")
        count2 = detector.record_attempt("task-1")
        count3 = detector.record_attempt("task-1")

        assert count1 == 1
        assert count2 == 2
        assert count3 == 3

    def test_should_retry_within_limits(self):
        """Test should_retry returns True within retry limits."""
        detector = LoopDetector(max_retries=3)

        detector.record_attempt("task-1")
        assert detector.should_retry("task-1") is True

        detector.record_attempt("task-1")
        assert detector.should_retry("task-1") is True

    def test_should_retry_exceeds_limits(self):
        """Test should_retry returns False after exceeding limits."""
        detector = LoopDetector(max_retries=3)

        # After 3 retries (max_retries), still can retry one more time
        for _ in range(3):
            detector.record_attempt("task-1")

        assert detector.should_retry("task-1") is True

        # 4th attempt exceeds limit
        detector.record_attempt("task-1")
        assert detector.should_retry("task-1") is False

    def test_reset_clears_counter(self):
        """Test that reset clears the attempt counter."""
        detector = LoopDetector(max_retries=3)

        detector.record_attempt("task-1")
        detector.record_attempt("task-1")
        detector.reset("task-1")

        assert detector.get_attempt_count("task-1") == 0
        assert detector.should_retry("task-1") is True

    def test_get_failed_tasks(self):
        """Test getting list of failed tasks."""
        detector = LoopDetector(max_retries=2)

        # Exceed retries for task-1
        detector.record_attempt("task-1")
        detector.record_attempt("task-1")
        detector.record_attempt("task-1")

        # Only 1 attempt for task-2
        detector.record_attempt("task-2")

        failed = detector.get_failed_tasks()
        assert "task-1" in failed
        assert "task-2" not in failed

    def test_get_task_info(self):
        """Test getting detailed task info."""
        detector = LoopDetector(max_retries=3)

        detector.record_attempt("task-1")
        info = detector.get_task_info("task-1")

        assert info is not None
        assert info["task_id"] == "task-1"
        assert info["attempt_count"] == 1
        assert info["max_retries"] == 3
        assert info["can_retry"] is True

    def test_configure_max_retries(self):
        """Test configuring max retries."""
        detector = LoopDetector(max_retries=3)
        detector.configure_max_retries(5)

        assert detector.max_retries == 5

    def test_clear_all_data(self):
        """Test clearing all tracking data."""
        detector = LoopDetector()

        detector.record_attempt("task-1")
        detector.record_attempt("task-2")
        detector.clear()

        assert detector.get_attempt_count("task-1") == 0
        assert detector.get_attempt_count("task-2") == 0

    def test_get_stats(self):
        """Test getting loop detector statistics."""
        detector = LoopDetector(max_retries=2)

        detector.record_attempt("task-1")
        detector.record_attempt("task-1")
        detector.record_attempt("task-1")  # Exceeds limit
        detector.record_attempt("task-2")

        stats = detector.get_stats()

        assert stats["total_tracked_tasks"] == 2
        assert stats["failed_tasks_count"] == 1
        assert stats["max_retries"] == 2


class TestTimeoutManager:
    """Tests for the TimeoutManager class."""

    def test_initialization(self):
        """Test TimeoutManager initialization."""
        manager = TimeoutManager()

        assert manager.timeouts["api_call"] == 60
        assert manager.timeouts["task"] == 300
        assert manager.timeouts["stage"] == 1800
        assert manager.timeouts["project"] == 7200

    @pytest.mark.asyncio
    async def test_run_with_timeout_success(self):
        """Test running a coroutine that completes in time."""
        manager = TimeoutManager()

        async def quick_operation():
            await asyncio.sleep(0.01)
            return "success"

        result = await manager.run_with_timeout(
            quick_operation(),
            timeout_type="api_call",
            task_id="test-1",
        )

        assert result == "success"

    @pytest.mark.asyncio
    async def test_run_with_timeout_exceeds(self):
        """Test that timeout raises TimeoutError."""
        manager = TimeoutManager()
        manager.configure_timeout("api_call", 1)  # 1 second timeout

        async def slow_operation():
            await asyncio.sleep(5)
            return "never reached"

        with pytest.raises(TimeoutError) as exc_info:
            await manager.run_with_timeout(
                slow_operation(),
                timeout_type="api_call",
                task_id="test-slow",
            )

        assert exc_info.value.timeout_type == "api_call"
        assert exc_info.value.timeout_seconds == 1

    @pytest.mark.asyncio
    async def test_run_with_timeout_invalid_type(self):
        """Test that invalid timeout type raises ValueError."""
        manager = TimeoutManager()

        async def some_operation():
            return "result"

        with pytest.raises(ValueError):
            await manager.run_with_timeout(
                some_operation(),
                timeout_type="invalid_type",
            )

    def test_configure_timeout(self):
        """Test configuring a timeout value."""
        manager = TimeoutManager()
        manager.configure_timeout("api_call", 120)

        assert manager.timeouts["api_call"] == 120

    def test_configure_timeout_invalid_value(self):
        """Test that non-positive timeout raises ValueError."""
        manager = TimeoutManager()

        with pytest.raises(ValueError):
            manager.configure_timeout("api_call", 0)

        with pytest.raises(ValueError):
            manager.configure_timeout("api_call", -10)

    def test_get_timeout(self):
        """Test getting a timeout value."""
        manager = TimeoutManager()

        assert manager.get_timeout("task") == 300
        assert manager.get_timeout("nonexistent") is None

    @pytest.mark.asyncio
    async def test_timeout_events_recorded(self):
        """Test that timeout events are recorded."""
        manager = TimeoutManager()
        manager.configure_timeout("api_call", 1)

        async def slow_operation():
            await asyncio.sleep(5)

        try:
            await manager.run_with_timeout(
                slow_operation(),
                timeout_type="api_call",
            )
        except TimeoutError:
            pass

        events = manager.get_timeout_events()
        assert len(events) == 1
        assert events[0]["timeout_type"] == "api_call"

    def test_reset_to_defaults(self):
        """Test resetting timeouts to defaults."""
        manager = TimeoutManager()
        manager.configure_timeout("api_call", 999)

        manager.reset_to_defaults()

        assert manager.timeouts["api_call"] == 60

    def test_get_stats(self):
        """Test getting timeout statistics."""
        manager = TimeoutManager()

        stats = manager.get_stats()

        assert "configured_timeouts" in stats
        assert "active_operations" in stats
        assert stats["total_timeout_events"] == 0


class TestCrashRecovery:
    """Tests for the CrashRecovery class."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield os.path.join(tmpdir, "test_recovery.db")

    @pytest.mark.asyncio
    async def test_initialization(self, temp_db_path):
        """Test CrashRecovery initialization."""
        recovery = CrashRecovery(db_path=temp_db_path)
        await recovery.initialize()

        assert recovery._initialized is True
        assert Path(temp_db_path).exists()

    @pytest.mark.asyncio
    async def test_save_and_get_checkpoint(self, temp_db_path):
        """Test saving and retrieving a checkpoint."""
        recovery = CrashRecovery(db_path=temp_db_path)
        await recovery.initialize()

        state = {"files": ["index.html"], "progress": 50}
        await recovery.save_checkpoint("proj-1", "development", state)

        checkpoint = await recovery.get_checkpoint("proj-1")

        assert checkpoint is not None
        assert checkpoint["project_id"] == "proj-1"
        assert checkpoint["stage"] == "development"
        assert checkpoint["state"]["files"] == ["index.html"]

    @pytest.mark.asyncio
    async def test_get_incomplete_projects(self, temp_db_path):
        """Test getting incomplete projects."""
        recovery = CrashRecovery(db_path=temp_db_path)
        await recovery.initialize()

        await recovery.save_checkpoint("proj-1", "development", {})
        await recovery.save_checkpoint("proj-2", "delivered", {})
        await recovery.save_checkpoint("proj-3", "testing", {})

        incomplete = await recovery.get_incomplete_projects()

        assert len(incomplete) == 2
        project_ids = [p["project_id"] for p in incomplete]
        assert "proj-1" in project_ids
        assert "proj-3" in project_ids
        assert "proj-2" not in project_ids  # delivered is terminal

    @pytest.mark.asyncio
    async def test_restore_project(self, temp_db_path):
        """Test restoring a project from checkpoint."""
        recovery = CrashRecovery(db_path=temp_db_path)
        await recovery.initialize()

        original_state = {"task_index": 5, "completed": ["t1", "t2"]}
        await recovery.save_checkpoint("proj-1", "development", original_state)

        restored = await recovery.restore_project("proj-1")

        assert restored is not None
        assert restored["project_id"] == "proj-1"
        assert restored["state"]["task_index"] == 5
        assert restored["recovered"] is True

    @pytest.mark.asyncio
    async def test_restore_nonexistent_project(self, temp_db_path):
        """Test restoring a project that doesn't exist."""
        recovery = CrashRecovery(db_path=temp_db_path)
        await recovery.initialize()

        restored = await recovery.restore_project("nonexistent")

        assert restored is None

    @pytest.mark.asyncio
    async def test_mark_completed(self, temp_db_path):
        """Test marking a project as completed."""
        recovery = CrashRecovery(db_path=temp_db_path)
        await recovery.initialize()

        await recovery.save_checkpoint("proj-1", "development", {})
        await recovery.mark_completed("proj-1")

        checkpoint = await recovery.get_checkpoint("proj-1")
        assert checkpoint is None

    @pytest.mark.asyncio
    async def test_update_checkpoint(self, temp_db_path):
        """Test updating an existing checkpoint."""
        recovery = CrashRecovery(db_path=temp_db_path)
        await recovery.initialize()

        await recovery.save_checkpoint("proj-1", "development", {"step": 1})
        await recovery.save_checkpoint("proj-1", "testing", {"step": 2})

        checkpoint = await recovery.get_checkpoint("proj-1")

        assert checkpoint["stage"] == "testing"
        assert checkpoint["state"]["step"] == 2

    @pytest.mark.asyncio
    async def test_recovery_history(self, temp_db_path):
        """Test recovery history recording."""
        recovery = CrashRecovery(db_path=temp_db_path)
        await recovery.initialize()

        await recovery.save_checkpoint("proj-1", "development", {})
        await recovery.restore_project("proj-1")

        history = await recovery.get_recovery_history("proj-1")

        assert len(history) == 1
        assert history[0]["project_id"] == "proj-1"
        assert history[0]["success"] is True

    @pytest.mark.asyncio
    async def test_get_stats(self, temp_db_path):
        """Test getting crash recovery statistics."""
        recovery = CrashRecovery(db_path=temp_db_path)
        await recovery.initialize()

        await recovery.save_checkpoint("proj-1", "development", {})
        await recovery.save_checkpoint("proj-2", "testing", {})

        stats = await recovery.get_stats()

        assert stats["total_checkpoints"] == 2
        assert "development" in stats["checkpoints_by_stage"]


class TestErrorRecovery:
    """Tests for the ErrorRecovery class."""

    def test_initialization(self):
        """Test ErrorRecovery initialization."""
        detector = LoopDetector()
        recovery = ErrorRecovery(detector)

        assert recovery.loop_detector is detector
        assert recovery.error_handler_agent is None

    @pytest.mark.asyncio
    async def test_handle_rate_limit_error(self):
        """Test handling rate limit errors."""
        detector = LoopDetector()
        recovery = ErrorRecovery(detector)

        error = Exception("Rate limit exceeded: 429")
        result = await recovery.handle_error(
            error, {"task_id": "task-1"}
        )

        assert result.action == RecoveryAction.RETRY
        assert result.error_type == ErrorType.RATE_LIMIT
        assert result.delay_seconds > 0

    @pytest.mark.asyncio
    async def test_handle_timeout_error(self):
        """Test handling timeout errors."""
        detector = LoopDetector()
        recovery = ErrorRecovery(detector)

        error = Exception("Operation timed out")
        result = await recovery.handle_error(
            error, {"task_id": "task-1"}
        )

        assert result.action == RecoveryAction.RETRY
        assert result.error_type == ErrorType.TIMEOUT

    @pytest.mark.asyncio
    async def test_handle_authentication_error(self):
        """Test handling authentication errors."""
        detector = LoopDetector()
        recovery = ErrorRecovery(detector)

        error = Exception("Unauthorized: 401")
        result = await recovery.handle_error(
            error, {"task_id": "task-1"}
        )

        assert result.action == RecoveryAction.ESCALATE
        assert result.error_type == ErrorType.AUTHENTICATION

    @pytest.mark.asyncio
    async def test_exceeded_retries_escalates(self):
        """Test that exceeding retries leads to escalation."""
        detector = LoopDetector(max_retries=3)
        recovery = ErrorRecovery(detector)

        # Use a connection error which is classified as TRANSIENT
        error = ConnectionError("Network connection failed")

        # First three attempts - retry
        for i in range(3):
            result = await recovery.handle_error(
                error, {"task_id": "task-1"}
            )
            assert result.action == RecoveryAction.RETRY, f"Attempt {i+1} should retry"

        # Fourth attempt - should escalate (exceeded max_retries of 3)
        result = await recovery.handle_error(
            error, {"task_id": "task-1"}
        )
        assert result.action in [RecoveryAction.ESCALATE, RecoveryAction.ABORT]

    @pytest.mark.asyncio
    async def test_mark_success_resets_counter(self):
        """Test that marking success resets the retry counter."""
        detector = LoopDetector(max_retries=3)
        recovery = ErrorRecovery(detector)

        error = Exception("Temporary error")

        await recovery.handle_error(error, {"task_id": "task-1"})
        await recovery.handle_error(error, {"task_id": "task-1"})

        recovery.mark_success("task-1")

        # After reset, should retry again
        result = await recovery.handle_error(error, {"task_id": "task-1"})
        assert result.action == RecoveryAction.RETRY

    @pytest.mark.asyncio
    async def test_recovery_history(self):
        """Test that recovery attempts are recorded."""
        detector = LoopDetector()
        recovery = ErrorRecovery(detector)

        error = Exception("Test error")
        await recovery.handle_error(error, {"task_id": "task-1"})

        history = recovery.get_recovery_history()

        assert len(history) == 1
        assert history[0]["task_id"] == "task-1"

    def test_get_stats(self):
        """Test getting error recovery statistics."""
        detector = LoopDetector()
        recovery = ErrorRecovery(detector)

        stats = recovery.get_stats()

        assert "total_recoveries" in stats
        assert "loop_detector_stats" in stats


class TestGracefulDegradation:
    """Tests for the GracefulDegradation class."""

    def test_initialization(self):
        """Test GracefulDegradation initialization."""
        degradation = GracefulDegradation()

        assert degradation.get_current_level() == DegradationLevel.NONE
        assert degradation.is_operational() is True

    def test_register_backup_agent(self):
        """Test registering backup agents."""
        degradation = GracefulDegradation()
        degradation.register_backup_agent("FrontendAgent", "HelperAgent")

        report = degradation.get_degradation_report()
        assert "FrontendAgent" in report["backup_agents"]

    def test_register_backup_provider(self):
        """Test registering backup providers."""
        degradation = GracefulDegradation()
        degradation.register_backup_provider("openai", "anthropic")

        report = degradation.get_degradation_report()
        assert "openai" in report["backup_providers"]

    @pytest.mark.asyncio
    async def test_on_agent_failure_with_backup(self):
        """Test agent failure when backup is available."""
        degradation = GracefulDegradation()
        degradation.register_backup_agent("FrontendAgent", "HelperAgent")

        error = Exception("Agent failed")
        action = await degradation.on_agent_failure("FrontendAgent", error)

        assert "switched_to_backup:HelperAgent" == action
        assert degradation.get_current_level() == DegradationLevel.MINOR

    @pytest.mark.asyncio
    async def test_on_agent_failure_critical(self):
        """Test critical agent failure."""
        degradation = GracefulDegradation()

        error = Exception("Critical failure")
        action = await degradation.on_agent_failure("Orchestrator", error)

        assert action == "failed:critical_agent"
        assert degradation.get_current_level() == DegradationLevel.CRITICAL
        assert degradation.is_operational() is False

    @pytest.mark.asyncio
    async def test_on_agent_failure_skipped(self):
        """Test non-critical agent failure without backup."""
        degradation = GracefulDegradation()

        error = Exception("Agent failed")
        action = await degradation.on_agent_failure("OptionalAgent", error)

        assert action == "skipped:OptionalAgent"
        assert degradation.get_current_level() == DegradationLevel.MODERATE

    @pytest.mark.asyncio
    async def test_on_api_failure_with_backup(self):
        """Test API failure when backup provider exists."""
        degradation = GracefulDegradation()
        degradation.register_backup_provider("openai", "anthropic")

        error = Exception("API error")
        action = await degradation.on_api_failure("openai", error)

        assert "switched_to_backup:anthropic" == action

    @pytest.mark.asyncio
    async def test_on_api_failure_no_backup(self):
        """Test API failure without backup provider."""
        degradation = GracefulDegradation()

        error = Exception("API error")
        action = await degradation.on_api_failure("gemini", error)

        assert "warning:no_backup_for_gemini" == action
        assert degradation.get_current_level() == DegradationLevel.SEVERE

    @pytest.mark.asyncio
    async def test_on_feature_unavailable_with_fallback(self):
        """Test feature unavailability with fallback."""
        degradation = GracefulDegradation()

        action = await degradation.on_feature_unavailable(
            "preview_server",
            "static file serving"
        )

        assert "fallback:static file serving" == action

    @pytest.mark.asyncio
    async def test_on_feature_unavailable_no_fallback(self):
        """Test feature unavailability without fallback."""
        degradation = GracefulDegradation()

        action = await degradation.on_feature_unavailable("analytics")

        assert "skipped:analytics" == action

    def test_get_degradation_report(self):
        """Test getting degradation report."""
        degradation = GracefulDegradation()

        report = degradation.get_degradation_report()

        assert "current_level" in report
        assert "total_events" in report
        assert "active_degradations" in report

    def test_clear_degradation(self):
        """Test clearing a degradation."""
        degradation = GracefulDegradation()

        # Add an event directly for testing
        from backend.core.graceful_degradation import DegradationEvent
        event = DegradationEvent(
            component="test",
            action=DegradationAction.SKIPPED_TASK,
            level=DegradationLevel.MINOR,
            message="Test",
        )
        degradation._events.append(event)
        degradation._active_degradations["test"] = event
        degradation._update_degradation_level()

        result = degradation.clear_degradation("test")

        assert result is True
        assert degradation.get_current_level() == DegradationLevel.NONE

    def test_reset(self):
        """Test resetting degradation tracking."""
        degradation = GracefulDegradation()

        # Add some events
        from backend.core.graceful_degradation import DegradationEvent
        event = DegradationEvent(
            component="test",
            action=DegradationAction.SKIPPED_TASK,
            level=DegradationLevel.MODERATE,
            message="Test",
        )
        degradation._events.append(event)
        degradation._active_degradations["test"] = event

        degradation.reset()

        assert len(degradation.get_events()) == 0
        assert degradation.get_current_level() == DegradationLevel.NONE


class TestIntegration:
    """Integration tests for error handling components."""

    @pytest.mark.asyncio
    async def test_error_recovery_with_loop_detection(self):
        """Test error recovery respects loop detection limits."""
        detector = LoopDetector(max_retries=3)
        recovery = ErrorRecovery(detector)

        # Use a connection error which is classified as TRANSIENT
        error = ConnectionError("Network connection failed")
        task_id = "integration-task"

        # Simulate multiple failures
        results = []
        for _ in range(5):
            result = await recovery.handle_error(error, {"task_id": task_id})
            results.append(result.action)

        # First 3 should retry, then escalate
        assert results[0] == RecoveryAction.RETRY
        assert results[1] == RecoveryAction.RETRY
        assert results[2] == RecoveryAction.RETRY
        assert results[3] in [RecoveryAction.ESCALATE, RecoveryAction.ABORT]

    @pytest.mark.asyncio
    async def test_timeout_with_graceful_degradation(self):
        """Test timeout handling with graceful degradation."""
        timeout_manager = TimeoutManager()
        timeout_manager.configure_timeout("api_call", 1)
        degradation = GracefulDegradation()
        degradation.register_backup_provider("primary", "backup")

        async def slow_api_call():
            await asyncio.sleep(5)

        try:
            await timeout_manager.run_with_timeout(
                slow_api_call(),
                timeout_type="api_call",
            )
        except TimeoutError:
            action = await degradation.on_api_failure(
                "primary",
                Exception("Timeout")
            )
            assert "switched_to_backup" in action

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield os.path.join(tmpdir, "test_integration.db")

    @pytest.mark.asyncio
    async def test_crash_recovery_workflow(self, temp_db_path):
        """Test complete crash recovery workflow."""
        recovery = CrashRecovery(db_path=temp_db_path)
        await recovery.initialize()

        # Simulate project progress
        await recovery.save_checkpoint("proj-1", "initialized", {"step": 0})
        await recovery.save_checkpoint("proj-1", "planning", {"step": 1})
        await recovery.save_checkpoint("proj-1", "development", {"step": 2})

        # Simulate crash and recovery
        incomplete = await recovery.get_incomplete_projects()
        assert len(incomplete) == 1

        restored = await recovery.restore_project("proj-1")
        assert restored["stage"] == "development"
        assert restored["state"]["step"] == 2

        # Complete the project
        await recovery.save_checkpoint("proj-1", "delivered", {"step": 3})
        await recovery.mark_completed("proj-1")

        incomplete = await recovery.get_incomplete_projects()
        assert len(incomplete) == 0
