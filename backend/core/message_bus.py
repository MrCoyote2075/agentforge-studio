"""
Message Bus module for AgentForge Studio.

This module provides a pub/sub messaging system for inter-agent
communication.
"""

import asyncio
from typing import Any, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Message:
    """
    Message class for the message bus.
    
    Attributes:
        id: Unique message identifier.
        topic: Message topic/channel.
        payload: Message content.
        sender: ID of the sender.
        priority: Message priority level.
        timestamp: When the message was created.
        metadata: Additional message metadata.
    """
    topic: str
    payload: Any
    sender: str = "system"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


class MessageBus:
    """
    Pub/Sub message bus for inter-agent communication.
    
    Provides asynchronous message passing between components with
    topic-based subscription and priority handling.
    
    Attributes:
        subscribers: Dictionary of topic to subscriber callbacks.
        message_queue: Queue of pending messages.
        running: Whether the message bus is running.
    """
    
    def __init__(self) -> None:
        """Initialize the message bus."""
        self._subscribers: dict[str, list[Callable[..., Any]]] = {}
        self._message_queue: asyncio.Queue[Message] = asyncio.Queue()
        self._running: bool = False
        self._processor_task: Optional[asyncio.Task[None]] = None
        self._message_history: list[Message] = []
        self._max_history: int = 1000
    
    @property
    def running(self) -> bool:
        """Check if the message bus is running."""
        return self._running
    
    async def start(self) -> None:
        """Start the message bus processor."""
        if self._running:
            return
        
        self._running = True
        self._processor_task = asyncio.create_task(self._process_messages())
    
    async def stop(self) -> None:
        """Stop the message bus processor."""
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
            self._processor_task = None
    
    def subscribe(
        self,
        topic: str,
        callback: Callable[..., Any]
    ) -> None:
        """
        Subscribe to a topic.
        
        Args:
            topic: The topic to subscribe to.
            callback: Callback function to handle messages.
        """
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(callback)
    
    def unsubscribe(
        self,
        topic: str,
        callback: Callable[..., Any]
    ) -> bool:
        """
        Unsubscribe from a topic.
        
        Args:
            topic: The topic to unsubscribe from.
            callback: The callback to remove.
            
        Returns:
            True if successfully unsubscribed, False otherwise.
        """
        if topic in self._subscribers:
            try:
                self._subscribers[topic].remove(callback)
                return True
            except ValueError:
                pass
        return False
    
    async def publish(
        self,
        topic: str,
        payload: Any,
        sender: str = "system",
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[dict[str, Any]] = None
    ) -> str:
        """
        Publish a message to a topic.
        
        Args:
            topic: The topic to publish to.
            payload: The message payload.
            sender: ID of the sender.
            priority: Message priority.
            metadata: Additional metadata.
            
        Returns:
            The message ID.
        """
        message = Message(
            topic=topic,
            payload=payload,
            sender=sender,
            priority=priority,
            metadata=metadata or {}
        )
        
        await self._message_queue.put(message)
        return message.id
    
    async def publish_and_wait(
        self,
        topic: str,
        payload: Any,
        sender: str = "system",
        timeout: float = 30.0
    ) -> list[Any]:
        """
        Publish a message and wait for responses.
        
        Args:
            topic: The topic to publish to.
            payload: The message payload.
            sender: ID of the sender.
            timeout: Timeout in seconds.
            
        Returns:
            List of responses from subscribers.
        """
        responses: list[Any] = []
        message = Message(
            topic=topic,
            payload=payload,
            sender=sender
        )
        
        if topic in self._subscribers:
            for callback in self._subscribers[topic]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        result = await asyncio.wait_for(
                            callback(message),
                            timeout=timeout
                        )
                    else:
                        result = callback(message)
                    responses.append(result)
                except asyncio.TimeoutError:
                    responses.append({"error": "timeout"})
                except Exception as e:
                    responses.append({"error": str(e)})
        
        return responses
    
    async def _process_messages(self) -> None:
        """Process messages from the queue."""
        while self._running:
            try:
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0
                )
                
                # Add to history
                self._message_history.append(message)
                if len(self._message_history) > self._max_history:
                    self._message_history.pop(0)
                
                # Dispatch to subscribers
                await self._dispatch(message)
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
    
    async def _dispatch(self, message: Message) -> None:
        """
        Dispatch a message to subscribers.
        
        Args:
            message: The message to dispatch.
        """
        if message.topic in self._subscribers:
            tasks = []
            for callback in self._subscribers[message.topic]:
                if asyncio.iscoroutinefunction(callback):
                    tasks.append(asyncio.create_task(callback(message)))
                else:
                    try:
                        callback(message)
                    except Exception:
                        pass
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_topics(self) -> list[str]:
        """
        Get all registered topics.
        
        Returns:
            List of topic names.
        """
        return list(self._subscribers.keys())
    
    def get_subscriber_count(self, topic: str) -> int:
        """
        Get the number of subscribers for a topic.
        
        Args:
            topic: The topic name.
            
        Returns:
            Number of subscribers.
        """
        return len(self._subscribers.get(topic, []))
    
    def get_message_history(
        self,
        topic: Optional[str] = None,
        limit: int = 100
    ) -> list[Message]:
        """
        Get message history.
        
        Args:
            topic: Optional topic filter.
            limit: Maximum number of messages to return.
            
        Returns:
            List of historical messages.
        """
        if topic:
            messages = [m for m in self._message_history if m.topic == topic]
        else:
            messages = self._message_history.copy()
        
        return messages[-limit:]
    
    def clear_history(self) -> None:
        """Clear the message history."""
        self._message_history.clear()
