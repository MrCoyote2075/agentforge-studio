"""
AgentForge Studio - Event Emitter.

This module implements an event-based communication system for real-time
updates between agents and the system.
"""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import Any
from uuid import uuid4

from backend.models.messages import Event, EventType

# Type alias for event handlers
EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventEmitter:
    """
    Event emitter for system-wide event handling.

    This class implements an event-based communication pattern that allows
    components to subscribe to and emit events. It supports:
    - Event registration and emission
    - Async event handlers
    - Event history for replay
    - Multiple handlers per event type

    Attributes:
        handlers: Dictionary mapping event types to handlers.
        event_history: List of past events for replay.

    Example:
        >>> emitter = EventEmitter()
        >>> async def on_file_created(event):
        ...     print(f"File created: {event.data['path']}")
        >>> emitter.on("file_created", on_file_created)
        >>> await emitter.emit("file_created", {"path": "index.html"})
    """

    def __init__(self, max_history: int = 1000) -> None:
        """
        Initialize the event emitter.

        Args:
            max_history: Maximum number of events to keep in history.
        """
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._event_history: list[Event] = []
        self._max_history = max_history
        self._running = False
        self._event_queue: asyncio.Queue[Event] = asyncio.Queue()
        self._processor_task: asyncio.Task | None = None
        self.logger = logging.getLogger("event_emitter")

    def on(
        self,
        event_type: str | EventType,
        handler: EventHandler,
    ) -> Callable[[], None]:
        """
        Register an event handler.

        Args:
            event_type: The event type to listen for.
            handler: Async callback function to handle the event.

        Returns:
            A function to unregister the handler.

        Example:
            >>> async def handler(event):
            ...     print(event.data)
            >>> unsubscribe = emitter.on("file_created", handler)
            >>> unsubscribe()  # Remove the handler
        """
        event_key = self._get_event_key(event_type)
        self._handlers[event_key].append(handler)

        self.logger.debug(f"Registered handler for event type '{event_key}'")

        def unsubscribe() -> None:
            if handler in self._handlers[event_key]:
                self._handlers[event_key].remove(handler)
                self.logger.debug(f"Unregistered handler for event type '{event_key}'")

        return unsubscribe

    def once(
        self,
        event_type: str | EventType,
        handler: EventHandler,
    ) -> Callable[[], None]:
        """
        Register a one-time event handler.

        The handler will be automatically removed after being called once.

        Args:
            event_type: The event type to listen for.
            handler: Async callback function to handle the event.

        Returns:
            A function to unregister the handler.
        """
        unsubscribe: Callable[[], None] | None = None

        async def wrapper(event: Event) -> None:
            await handler(event)
            if unsubscribe:
                unsubscribe()

        unsubscribe = self.on(event_type, wrapper)
        return unsubscribe

    def off(
        self,
        event_type: str | EventType,
        handler: EventHandler | None = None,
    ) -> int:
        """
        Remove event handler(s).

        Args:
            event_type: The event type.
            handler: Specific handler to remove. If None, removes all handlers.

        Returns:
            int: Number of handlers removed.
        """
        event_key = self._get_event_key(event_type)

        if handler:
            if handler in self._handlers[event_key]:
                self._handlers[event_key].remove(handler)
                return 1
            return 0
        else:
            count = len(self._handlers[event_key])
            self._handlers[event_key].clear()
            return count

    async def emit(
        self,
        event_type: str | EventType,
        data: dict[str, Any] | None = None,
        source: str = "system",
    ) -> Event:
        """
        Emit an event to all registered handlers.

        Args:
            event_type: The event type to emit.
            data: Event data/payload.
            source: Source of the event.

        Returns:
            The emitted event.
        """
        event_key = self._get_event_key(event_type)

        # Create the event
        event_enum = self._get_event_type_enum(event_key)
        event = Event(
            id=str(uuid4()),
            type=event_enum,
            source=source,
            data=data or {},
            timestamp=datetime.utcnow(),
        )

        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # Notify handlers
        handlers = self._handlers.get(event_key, [])
        for handler in handlers[:]:  # Copy list in case handlers modify it
            try:
                await handler(event)
            except Exception as e:
                self.logger.error(f"Error in event handler for '{event_key}': {e}")

        self.logger.debug(
            f"Emitted event '{event_key}' to {len(handlers)} handlers"
        )
        return event

    async def emit_async(
        self,
        event_type: str | EventType,
        data: dict[str, Any] | None = None,
        source: str = "system",
    ) -> None:
        """
        Queue an event for asynchronous emission.

        This method queues the event for processing by the background processor.

        Args:
            event_type: The event type to emit.
            data: Event data/payload.
            source: Source of the event.
        """
        event_key = self._get_event_key(event_type)
        event_enum = self._get_event_type_enum(event_key)

        event = Event(
            id=str(uuid4()),
            type=event_enum,
            source=source,
            data=data or {},
            timestamp=datetime.utcnow(),
        )

        await self._event_queue.put(event)

    async def start(self) -> None:
        """
        Start the event processor for async emission.

        This starts a background task that processes queued events.
        """
        if not self._running:
            self._running = True
            self._processor_task = asyncio.create_task(self._process_events())
            self.logger.info("Event emitter started")

    async def stop(self) -> None:
        """
        Stop the event processor.

        This stops the background processing task gracefully.
        """
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Event emitter stopped")

    async def _process_events(self) -> None:
        """Background task to process queued events."""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0,
                )

                # Store in history
                self._event_history.append(event)
                if len(self._event_history) > self._max_history:
                    self._event_history.pop(0)

                # Get the event type key
                event_key = self._get_event_key(event.type)

                # Notify handlers
                handlers = self._handlers.get(event_key, [])
                for handler in handlers[:]:
                    try:
                        await handler(event)
                    except Exception as e:
                        self.logger.error(
                            f"Error in event handler for '{event_key}': {e}"
                        )

                self._event_queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error processing event: {e}")

    def get_event_history(
        self,
        event_type: str | EventType | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """
        Get event history.

        Args:
            event_type: Optional event type to filter by.
            limit: Maximum number of events to return.

        Returns:
            List of past events.
        """
        events = self._event_history[-limit:]

        if event_type:
            event_key = self._get_event_key(event_type)
            events = [
                e for e in events
                if self._get_event_key(e.type) == event_key
            ]

        return events

    def replay_events(
        self,
        event_type: str | EventType | None = None,
        since: datetime | None = None,
    ) -> list[Event]:
        """
        Get events for replay.

        Args:
            event_type: Optional event type to filter by.
            since: Optional datetime to filter events after.

        Returns:
            List of events for replay.
        """
        events = self._event_history

        if since:
            events = [e for e in events if e.timestamp >= since]

        if event_type:
            event_key = self._get_event_key(event_type)
            events = [
                e for e in events
                if self._get_event_key(e.type) == event_key
            ]

        return events

    def get_handler_count(self, event_type: str | EventType | None = None) -> int:
        """
        Get the number of registered handlers.

        Args:
            event_type: Optional event type to count handlers for.

        Returns:
            int: Number of handlers.
        """
        if event_type:
            event_key = self._get_event_key(event_type)
            return len(self._handlers.get(event_key, []))
        return sum(len(handlers) for handlers in self._handlers.values())

    def get_event_types(self) -> list[str]:
        """
        Get all event types with registered handlers.

        Returns:
            List of event type names.
        """
        return list(self._handlers.keys())

    def _get_event_key(self, event_type: str | EventType) -> str:
        """Get the string key for an event type."""
        if isinstance(event_type, EventType):
            return event_type.value
        return event_type

    def _get_event_type_enum(self, event_key: str) -> EventType:
        """Get the EventType enum for a string key."""
        if event_key in EventType._value2member_map_:
            return EventType(event_key)
        return EventType.AGENT_STARTED

    def clear_history(self) -> None:
        """Clear the event history."""
        self._event_history.clear()
        self.logger.info("Event history cleared")

    def clear_handlers(self) -> None:
        """Clear all event handlers."""
        self._handlers.clear()
        self.logger.info("Event handlers cleared")
