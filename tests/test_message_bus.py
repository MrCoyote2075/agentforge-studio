"""
Tests for Message Bus and Agent Communication System.

These tests verify that the inter-agent communication components
work correctly, including message passing, task queuing, event
emission, file locking, and agent registry.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from backend.core.agent_registry import AgentRegistry
from backend.core.event_emitter import EventEmitter
from backend.core.file_lock_manager import (
    FileLockContext,
    FileLockManager,
    LockAcquisitionError,
)
from backend.core.message_bus import MessageBus
from backend.core.task_queue import AsyncTaskQueue, TaskQueue
from backend.models.messages import (
    AgentInfo,
    AgentStatusType,
    ErrorMessage,
    Event,
    EventType,
    MessageType,
    ResultMessage,
    StatusMessage,
    Task,
    TaskMessage,
    TaskPriority,
    TaskState,
)
from backend.models.messages import Message as BusMessage
from backend.models.schemas import Message


class TestMessageModels:
    """Tests for message models."""

    def test_message_creation(self):
        """Test creating a basic message."""
        msg = BusMessage(
            from_agent="planner",
            to_agent="frontend_agent",
            type=MessageType.TASK,
            payload={"action": "create_html"},
        )
        assert msg.from_agent == "planner"
        assert msg.to_agent == "frontend_agent"
        assert msg.type == MessageType.TASK
        assert msg.id is not None
        assert msg.timestamp is not None

    def test_task_message_creation(self):
        """Test creating a task message."""
        msg = TaskMessage(
            from_agent="planner",
            to_agent="frontend_agent",
            task_description="Create homepage HTML",
            dependencies=["task-0"],
        )
        assert msg.type == MessageType.TASK
        assert msg.task_description == "Create homepage HTML"
        assert "task-0" in msg.dependencies

    def test_result_message_creation(self):
        """Test creating a result message."""
        msg = ResultMessage(
            from_agent="frontend_agent",
            to_agent="planner",
            task_id="task-1",
            success=True,
            result={"file": "index.html"},
        )
        assert msg.type == MessageType.RESULT
        assert msg.success is True
        assert msg.task_id == "task-1"

    def test_status_message_creation(self):
        """Test creating a status message."""
        msg = StatusMessage(
            from_agent="frontend_agent",
            agent_name="frontend_agent",
            status=AgentStatusType.BUSY,
            current_task="Building homepage",
            progress=50.0,
        )
        assert msg.type == MessageType.STATUS
        assert msg.status == AgentStatusType.BUSY
        assert msg.progress == 50.0

    def test_error_message_creation(self):
        """Test creating an error message."""
        msg = ErrorMessage(
            from_agent="frontend_agent",
            error_code="E001",
            error_message="File not found",
            recoverable=True,
        )
        assert msg.type == MessageType.ERROR
        assert msg.error_code == "E001"
        assert msg.recoverable is True

    def test_event_creation(self):
        """Test creating an event."""
        event = Event(
            type=EventType.FILE_CREATED,
            source="frontend_agent",
            data={"path": "index.html"},
        )
        assert event.type == EventType.FILE_CREATED
        assert event.source == "frontend_agent"
        assert event.data["path"] == "index.html"

    def test_task_creation(self):
        """Test creating a task."""
        task = Task(
            type="create_html",
            description="Create the homepage",
            agent="frontend_agent",
            priority=TaskPriority.HIGH,
            dependencies=["task-0"],
        )
        assert task.type == "create_html"
        assert task.state == TaskState.PENDING
        assert task.priority == TaskPriority.HIGH

    def test_agent_info_creation(self):
        """Test creating agent info."""
        info = AgentInfo(
            name="frontend_agent",
            status=AgentStatusType.IDLE,
            capabilities=["html", "css", "js"],
        )
        assert info.name == "frontend_agent"
        assert info.status == AgentStatusType.IDLE
        assert "html" in info.capabilities


class TestMessageBus:
    """Tests for the MessageBus class."""

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self):
        """Test basic subscribe and publish."""
        bus = MessageBus()
        received_messages = []

        async def handler(msg: Message) -> None:
            received_messages.append(msg)

        await bus.subscribe("test_topic", handler, "test_agent")
        
        msg = Message(
            from_agent="sender",
            to_agent="test_agent",
            content="Hello",
        )
        delivered = await bus.publish("test_topic", msg)

        assert delivered == 1
        assert len(received_messages) == 1
        assert received_messages[0].content == "Hello"

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        """Test unsubscribing from a topic."""
        bus = MessageBus()
        received_messages = []

        async def handler(msg: Message) -> None:
            received_messages.append(msg)

        sub_id = await bus.subscribe("test_topic", handler, "test_agent")
        assert bus.get_subscription_count("test_topic") == 1

        await bus.unsubscribe(sub_id)
        assert bus.get_subscription_count("test_topic") == 0

    @pytest.mark.asyncio
    async def test_unsubscribe_agent(self):
        """Test unsubscribing all subscriptions for an agent."""
        bus = MessageBus()

        async def handler(msg: Message) -> None:
            pass

        await bus.subscribe("topic1", handler, "test_agent")
        await bus.subscribe("topic2", handler, "test_agent")
        assert bus.get_subscription_count() == 2

        count = await bus.unsubscribe_agent("test_agent")
        assert count == 2
        assert bus.get_subscription_count() == 0

    @pytest.mark.asyncio
    async def test_broadcast(self):
        """Test broadcasting a message."""
        bus = MessageBus()
        received_messages = []

        async def handler(msg: Message) -> None:
            received_messages.append(msg)

        await bus.subscribe("topic1", handler, "agent1")
        await bus.subscribe("topic2", handler, "agent2")

        msg = Message(from_agent="sender", to_agent="all", content="Broadcast")
        total = await bus.broadcast(msg)

        assert total == 2
        assert len(received_messages) == 2

    @pytest.mark.asyncio
    async def test_message_history(self):
        """Test message history tracking."""
        bus = MessageBus(max_history=10)

        async def handler(msg: Message) -> None:
            pass

        await bus.subscribe("test", handler, "agent")

        for i in range(5):
            msg = Message(
                from_agent="sender",
                to_agent="agent",
                content=f"Message {i}",
            )
            await bus.publish("test", msg)

        history = bus.get_message_history(limit=3)
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_get_topics(self):
        """Test getting all topics."""
        bus = MessageBus()

        async def handler(msg: Message) -> None:
            pass

        await bus.subscribe("topic1", handler, "agent1")
        await bus.subscribe("topic2", handler, "agent2")

        topics = bus.get_topics()
        assert "topic1" in topics
        assert "topic2" in topics


class TestTaskQueue:
    """Tests for the TaskQueue class."""

    def test_add_and_get_task(self):
        """Test adding and getting a task."""
        queue = TaskQueue()
        task = Task(
            type="create_html",
            description="Build homepage",
        )
        
        task_id = queue.add_task(task)
        retrieved = queue.get_task(task_id)

        assert retrieved is not None
        assert retrieved.type == "create_html"

    def test_get_next_task(self):
        """Test getting the next available task."""
        queue = TaskQueue()
        task = Task(
            type="create_html",
            description="Build homepage",
        )
        queue.add_task(task)

        next_task = queue.get_next_task("frontend_agent")

        assert next_task is not None
        assert next_task.agent == "frontend_agent"
        assert next_task.state == TaskState.IN_PROGRESS

    def test_priority_ordering(self):
        """Test that high priority tasks are returned first."""
        queue = TaskQueue()

        low = Task(type="low", description="Low priority", priority=TaskPriority.LOW)
        high = Task(type="high", description="High priority", priority=TaskPriority.HIGH)
        medium = Task(type="medium", description="Medium priority", priority=TaskPriority.MEDIUM)

        queue.add_task(low)
        queue.add_task(medium)
        queue.add_task(high)

        # Should get high priority first
        first = queue.get_next_task("agent")
        assert first is not None
        assert first.priority == TaskPriority.HIGH

        second = queue.get_next_task("agent")
        assert second is not None
        assert second.priority == TaskPriority.MEDIUM

    def test_task_dependencies(self):
        """Test task dependency handling."""
        queue = TaskQueue()

        task1 = Task(id="task-1", type="first", description="First task")
        task2 = Task(
            id="task-2",
            type="second",
            description="Second task",
            dependencies=["task-1"],
        )

        queue.add_task(task1)
        queue.add_task(task2)

        # task2 should be blocked
        retrieved = queue.get_task("task-2")
        assert retrieved is not None
        assert retrieved.state == TaskState.BLOCKED

        # Get and complete task1
        next_task = queue.get_next_task("agent")
        assert next_task is not None
        assert next_task.id == "task-1"

        queue.complete_task("task-1", result="done")

        # task2 should now be available
        retrieved = queue.get_task("task-2")
        assert retrieved is not None
        assert retrieved.state == TaskState.PENDING

    def test_complete_task(self):
        """Test completing a task."""
        queue = TaskQueue()
        task = Task(type="test", description="Test task")
        queue.add_task(task)

        queue.get_next_task("agent")
        queue.complete_task(task.id, result={"status": "done"})

        completed = queue.get_task(task.id)
        assert completed is not None
        assert completed.state == TaskState.COMPLETED
        assert completed.result == {"status": "done"}
        assert completed.completed_at is not None

    def test_task_failure(self):
        """Test failing a task."""
        queue = TaskQueue()
        task = Task(type="test", description="Test task")
        queue.add_task(task)

        queue.get_next_task("agent")
        queue.complete_task(task.id, error="Something went wrong")

        failed = queue.get_task(task.id)
        assert failed is not None
        assert failed.state == TaskState.FAILED
        assert failed.error == "Something went wrong"

    def test_cancel_task(self):
        """Test canceling a task."""
        queue = TaskQueue()
        task = Task(type="test", description="Test task")
        queue.add_task(task)

        success = queue.cancel_task(task.id)
        assert success is True

        cancelled = queue.get_task(task.id)
        assert cancelled is not None
        assert cancelled.state == TaskState.FAILED
        assert cancelled.error == "Cancelled"

    def test_get_tasks_by_state(self):
        """Test getting tasks by state."""
        queue = TaskQueue()
        
        for i in range(3):
            task = Task(type="test", description=f"Task {i}")
            queue.add_task(task)

        queue.get_next_task("agent")  # Mark one as in-progress

        pending = queue.get_tasks_by_state(TaskState.PENDING)
        in_progress = queue.get_tasks_by_state(TaskState.IN_PROGRESS)

        assert len(pending) == 2
        assert len(in_progress) == 1


class TestAsyncTaskQueue:
    """Tests for the AsyncTaskQueue class."""

    @pytest.mark.asyncio
    async def test_async_add_and_get(self):
        """Test async task operations."""
        queue = AsyncTaskQueue()
        task = Task(type="test", description="Test task")

        task_id = await queue.add_task(task)
        retrieved = await queue.get_task(task_id)

        assert retrieved is not None
        assert retrieved.type == "test"

    @pytest.mark.asyncio
    async def test_wait_for_task(self):
        """Test waiting for task completion."""
        queue = AsyncTaskQueue()
        task = Task(type="test", description="Test task")
        await queue.add_task(task)

        async def complete_task():
            await asyncio.sleep(0.1)
            await queue.get_next_task("agent")
            await queue.complete_task(task.id, result="done")

        asyncio.create_task(complete_task())
        result = await queue.wait_for_task(task.id, timeout=1.0)

        assert result is not None
        assert result.state == TaskState.COMPLETED


class TestEventEmitter:
    """Tests for the EventEmitter class."""

    @pytest.mark.asyncio
    async def test_on_and_emit(self):
        """Test event registration and emission."""
        emitter = EventEmitter()
        received_events = []

        async def handler(event: Event) -> None:
            received_events.append(event)

        emitter.on("file_created", handler)
        await emitter.emit("file_created", {"path": "index.html"}, source="test")

        assert len(received_events) == 1
        assert received_events[0].data["path"] == "index.html"

    @pytest.mark.asyncio
    async def test_once_handler(self):
        """Test one-time event handler."""
        emitter = EventEmitter()
        call_count = 0

        async def handler(event: Event) -> None:
            nonlocal call_count
            call_count += 1

        emitter.once("test_event", handler)
        await emitter.emit("test_event")
        await emitter.emit("test_event")

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_off_handler(self):
        """Test removing event handlers."""
        emitter = EventEmitter()
        received = []

        async def handler(event: Event) -> None:
            received.append(event)

        emitter.on("test", handler)
        await emitter.emit("test")
        
        emitter.off("test", handler)
        await emitter.emit("test")

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_event_history(self):
        """Test event history."""
        emitter = EventEmitter(max_history=10)

        for i in range(5):
            await emitter.emit("test", {"index": i}, source="test")

        history = emitter.get_event_history(limit=3)
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_event_types_enum(self):
        """Test using EventType enum."""
        emitter = EventEmitter()
        received = []

        async def handler(event: Event) -> None:
            received.append(event)

        emitter.on(EventType.FILE_CREATED, handler)
        await emitter.emit(EventType.FILE_CREATED, {"path": "test.html"})

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_get_handler_count(self):
        """Test getting handler count."""
        emitter = EventEmitter()

        async def handler(event: Event) -> None:
            pass

        emitter.on("event1", handler)
        emitter.on("event2", handler)
        emitter.on("event2", handler)

        assert emitter.get_handler_count("event1") == 1
        assert emitter.get_handler_count("event2") == 2
        assert emitter.get_handler_count() == 3


class TestFileLockManager:
    """Tests for the FileLockManager class."""

    @pytest.mark.asyncio
    async def test_acquire_and_release(self):
        """Test acquiring and releasing a lock."""
        manager = FileLockManager()

        acquired = await manager.acquire("test.html", "frontend_agent")
        assert acquired is True

        is_locked = await manager.is_locked("test.html")
        assert is_locked is True

        released = await manager.release("test.html", "frontend_agent")
        assert released is True

        is_locked = await manager.is_locked("test.html")
        assert is_locked is False

    @pytest.mark.asyncio
    async def test_lock_conflict(self):
        """Test that a second agent cannot acquire a locked file."""
        manager = FileLockManager()

        await manager.acquire("test.html", "agent1")
        acquired = await manager.acquire("test.html", "agent2", wait=False)

        assert acquired is False

    @pytest.mark.asyncio
    async def test_get_lock_owner(self):
        """Test getting the lock owner."""
        manager = FileLockManager()

        await manager.acquire("test.html", "frontend_agent")
        owner = await manager.get_lock_owner("test.html")

        assert owner == "frontend_agent"

    @pytest.mark.asyncio
    async def test_lock_timeout(self):
        """Test that locks expire after timeout."""
        manager = FileLockManager()

        await manager.acquire("test.html", "agent1", timeout=0.1)
        await asyncio.sleep(0.2)

        # Lock should be expired, another agent can acquire
        acquired = await manager.acquire("test.html", "agent2", wait=False)
        assert acquired is True

    @pytest.mark.asyncio
    async def test_extend_lock(self):
        """Test extending a lock timeout."""
        manager = FileLockManager()

        await manager.acquire("test.html", "agent1", timeout=1.0)
        extended = await manager.extend_lock("test.html", "agent1", 10.0)

        assert extended is True

        lock_info = await manager.get_lock_info("test.html")
        assert lock_info is not None
        assert lock_info.timeout == 11.0

    @pytest.mark.asyncio
    async def test_release_all_for_agent(self):
        """Test releasing all locks for an agent."""
        manager = FileLockManager()

        await manager.acquire("file1.html", "agent1")
        await manager.acquire("file2.html", "agent1")
        await manager.acquire("file3.html", "agent2")

        count = await manager.release_all("agent1")
        assert count == 2

        locks = await manager.get_all_locks()
        assert len(locks) == 1
        assert locks[0].owner == "agent2"

    @pytest.mark.asyncio
    async def test_wrong_owner_cannot_release(self):
        """Test that wrong owner cannot release a lock."""
        manager = FileLockManager()

        await manager.acquire("test.html", "agent1")
        released = await manager.release("test.html", "agent2")

        assert released is False
        is_locked = await manager.is_locked("test.html")
        assert is_locked is True

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test file lock context manager."""
        manager = FileLockManager()

        async with FileLockContext(manager, "test.html", "agent1"):
            is_locked = await manager.is_locked("test.html")
            assert is_locked is True

        is_locked = await manager.is_locked("test.html")
        assert is_locked is False

    @pytest.mark.asyncio
    async def test_context_manager_acquisition_failure(self):
        """Test context manager raises error on acquisition failure."""
        manager = FileLockManager()

        await manager.acquire("test.html", "agent1")

        with pytest.raises(LockAcquisitionError):
            async with FileLockContext(
                manager, "test.html", "agent2", wait=False
            ):
                pass


class TestAgentRegistry:
    """Tests for the AgentRegistry class."""

    def test_register_and_get_agent(self):
        """Test registering and getting an agent."""
        registry = AgentRegistry()
        agent = registry.register(
            "frontend_agent",
            capabilities=["html", "css", "js"],
        )

        assert agent.name == "frontend_agent"
        assert "html" in agent.capabilities

        retrieved = registry.get_agent("frontend_agent")
        assert retrieved is not None
        assert retrieved.name == "frontend_agent"

    def test_unregister(self):
        """Test unregistering an agent."""
        registry = AgentRegistry()
        registry.register("test_agent")

        success = registry.unregister("test_agent")
        assert success is True

        agent = registry.get_agent("test_agent")
        assert agent is None

    def test_update_status(self):
        """Test updating agent status."""
        registry = AgentRegistry()
        registry.register("test_agent")

        registry.update_status(
            "test_agent",
            AgentStatusType.BUSY,
            current_task_id="task-1",
        )

        agent = registry.get_agent("test_agent")
        assert agent is not None
        assert agent.status == AgentStatusType.BUSY
        assert agent.current_task_id == "task-1"

    def test_get_available_agents(self):
        """Test getting available agents."""
        registry = AgentRegistry()
        registry.register("agent1", capabilities=["html"])
        registry.register("agent2", capabilities=["html"])
        registry.register("agent3", capabilities=["css"])

        registry.update_status("agent2", AgentStatusType.BUSY)

        available = registry.get_available_agents("html")
        assert len(available) == 1
        assert available[0].name == "agent1"

    def test_get_agents_by_capability(self):
        """Test getting agents by capability."""
        registry = AgentRegistry()
        registry.register("agent1", capabilities=["html", "css"])
        registry.register("agent2", capabilities=["html"])
        registry.register("agent3", capabilities=["js"])

        html_agents = registry.get_agents_by_capability("html")
        assert len(html_agents) == 2

    def test_heartbeat(self):
        """Test heartbeat recording."""
        registry = AgentRegistry(heartbeat_timeout=0.1)
        registry.register("test_agent")

        # Record heartbeat
        success = registry.heartbeat("test_agent")
        assert success is True

        # Agent should be healthy
        assert registry.is_healthy("test_agent") is True

    def test_add_and_remove_capability(self):
        """Test adding and removing capabilities."""
        registry = AgentRegistry()
        registry.register("test_agent", capabilities=["html"])

        registry.add_capability("test_agent", "css")
        agent = registry.get_agent("test_agent")
        assert agent is not None
        assert "css" in agent.capabilities

        registry.remove_capability("test_agent", "css")
        agent = registry.get_agent("test_agent")
        assert agent is not None
        assert "css" not in agent.capabilities

    def test_get_all_capabilities(self):
        """Test getting all capabilities."""
        registry = AgentRegistry()
        registry.register("agent1", capabilities=["html", "css"])
        registry.register("agent2", capabilities=["js"])

        capabilities = registry.get_all_capabilities()
        assert "html" in capabilities
        assert "css" in capabilities
        assert "js" in capabilities

    def test_get_agents_by_status(self):
        """Test getting agents by status."""
        registry = AgentRegistry()
        registry.register("agent1")
        registry.register("agent2")
        registry.register("agent3")

        registry.update_status("agent2", AgentStatusType.BUSY)
        registry.update_status("agent3", AgentStatusType.BUSY)

        idle = registry.get_agents_by_status(AgentStatusType.IDLE)
        busy = registry.get_agents_by_status(AgentStatusType.BUSY)

        assert len(idle) == 1
        assert len(busy) == 2

    def test_clear(self):
        """Test clearing the registry."""
        registry = AgentRegistry()
        registry.register("agent1", capabilities=["html"])
        registry.register("agent2", capabilities=["css"])

        registry.clear()

        assert registry.get_agent_count() == 0
        assert len(registry.get_all_capabilities()) == 0


class TestIntegration:
    """Integration tests for the message bus system."""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test a complete workflow with all components."""
        # Setup components
        bus = MessageBus()
        queue = AsyncTaskQueue()
        emitter = EventEmitter()
        lock_manager = FileLockManager()
        registry = AgentRegistry()

        # Register agents
        registry.register("planner", capabilities=["planning"])
        registry.register("frontend_agent", capabilities=["html", "css", "js"])

        # Track events
        events_received = []

        async def event_handler(event: Event) -> None:
            events_received.append(event)

        emitter.on(EventType.FILE_CREATED, event_handler)

        # Create and process a task
        task = Task(
            type="create_html",
            description="Create homepage",
            priority=TaskPriority.HIGH,
        )
        await queue.add_task(task)

        # Agent picks up task
        next_task = await queue.get_next_task("frontend_agent")
        assert next_task is not None

        # Update agent status
        registry.update_status(
            "frontend_agent",
            AgentStatusType.BUSY,
            current_task_id=next_task.id,
        )

        # Acquire file lock
        await lock_manager.acquire("index.html", "frontend_agent")

        # Emit file created event
        await emitter.emit(
            EventType.FILE_CREATED,
            {"path": "index.html"},
            source="frontend_agent",
        )

        # Release lock and complete task
        await lock_manager.release("index.html", "frontend_agent")
        await queue.complete_task(next_task.id, result={"file": "index.html"})

        # Update agent status back to idle
        registry.update_status("frontend_agent", AgentStatusType.IDLE)

        # Verify results
        assert len(events_received) == 1
        assert events_received[0].data["path"] == "index.html"

        completed_task = await queue.get_task(next_task.id)
        assert completed_task is not None
        assert completed_task.state == TaskState.COMPLETED

        agent = registry.get_agent("frontend_agent")
        assert agent is not None
        assert agent.status == AgentStatusType.IDLE
