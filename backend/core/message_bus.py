"""
AgentForge Studio - Message Bus.

This module implements a publish/subscribe pattern for inter-agent
communication. Agents can publish messages to topics and subscribe
to receive messages from other agents.
"""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import Any
from uuid import uuid4

from backend.models.schemas import Message

# Type alias for message handlers
MessageHandler = Callable[[Message], Coroutine[Any, Any, None]]


class Subscription:
    """
    Represents a subscription to the message bus.

    Attributes:
        id: Unique subscription identifier.
        topic: The topic being subscribed to.
        handler: The async callback function.
        subscriber_name: Name of the subscribing agent.
    """

    def __init__(
        self,
        topic: str,
        handler: MessageHandler,
        subscriber_name: str,
    ) -> None:
        """
        Initialize a subscription.

        Args:
            topic: Topic to subscribe to.
            handler: Async callback function for messages.
            subscriber_name: Name of the subscriber.
        """
        self.id = str(uuid4())
        self.topic = topic
        self.handler = handler
        self.subscriber_name = subscriber_name
        self.created_at = datetime.utcnow()


class MessageBus:
    """
    Central message bus for agent communication.

    The MessageBus implements a publish/subscribe pattern that allows
    agents to communicate asynchronously. Messages can be broadcast
    to topics or sent directly to specific agents.

    Attributes:
        subscriptions: Dictionary mapping topics to subscriptions.
        message_queue: Async queue for message processing.
        message_history: List of recent messages for debugging.

    Example:
        >>> bus = MessageBus()
        >>> await bus.subscribe("frontend", handler, "FrontendAgent")
        >>> await bus.publish("frontend", message)
    """

    def __init__(self, max_history: int = 1000) -> None:
        """
        Initialize the message bus.

        Args:
            max_history: Maximum number of messages to keep in history.
        """
        self._subscriptions: dict[str, list[Subscription]] = defaultdict(list)
        self._agent_subscriptions: dict[str, set[str]] = defaultdict(set)
        self._message_queue: asyncio.Queue[Message] = asyncio.Queue()
        self._message_history: list[Message] = []
        self._max_history = max_history
        self._running = False
        self._processor_task: asyncio.Task | None = None
        self.logger = logging.getLogger("message_bus")

    async def start(self) -> None:
        """
        Start the message bus processor.

        This starts a background task that processes queued messages.
        """
        if not self._running:
            self._running = True
            self._processor_task = asyncio.create_task(self._process_messages())
            self.logger.info("Message bus started")

    async def stop(self) -> None:
        """
        Stop the message bus processor.

        This stops the background processing task gracefully.
        """
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Message bus stopped")

    async def subscribe(
        self,
        topic: str,
        handler: MessageHandler,
        subscriber_name: str,
    ) -> str:
        """
        Subscribe to a topic.

        Args:
            topic: The topic to subscribe to.
            handler: Async callback function to handle messages.
            subscriber_name: Name of the subscribing agent.

        Returns:
            str: The subscription ID.

        Example:
            >>> async def my_handler(msg):
            ...     print(f"Received: {msg.content}")
            >>> sub_id = await bus.subscribe("tasks", my_handler, "MyAgent")
        """
        subscription = Subscription(topic, handler, subscriber_name)
        self._subscriptions[topic].append(subscription)
        self._agent_subscriptions[subscriber_name].add(subscription.id)

        self.logger.info(
            f"Agent '{subscriber_name}' subscribed to topic '{topic}' "
            f"(subscription: {subscription.id})"
        )
        return subscription.id

    async def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from a topic.

        Args:
            subscription_id: The subscription ID to remove.

        Returns:
            bool: True if subscription was removed, False if not found.
        """
        for topic, subs in self._subscriptions.items():
            for sub in subs:
                if sub.id == subscription_id:
                    subs.remove(sub)
                    self._agent_subscriptions[sub.subscriber_name].discard(
                        subscription_id
                    )
                    self.logger.info(
                        f"Subscription {subscription_id} removed from topic '{topic}'"
                    )
                    return True
        return False

    async def unsubscribe_agent(self, agent_name: str) -> int:
        """
        Remove all subscriptions for an agent.

        Args:
            agent_name: Name of the agent to unsubscribe.

        Returns:
            int: Number of subscriptions removed.
        """
        sub_ids = list(self._agent_subscriptions.get(agent_name, set()))
        count = 0
        for sub_id in sub_ids:
            if await self.unsubscribe(sub_id):
                count += 1
        return count

    async def publish(self, topic: str, message: Message) -> int:
        """
        Publish a message to a topic.

        Args:
            topic: The topic to publish to.
            message: The message to publish.

        Returns:
            int: Number of subscribers that received the message.
        """
        # Add to history
        self._message_history.append(message)
        if len(self._message_history) > self._max_history:
            self._message_history.pop(0)

        # Get subscribers for this topic
        subscribers = self._subscriptions.get(topic, [])
        delivered = 0

        for subscription in subscribers:
            try:
                await subscription.handler(message)
                delivered += 1
            except Exception as e:
                self.logger.error(
                    f"Error delivering message to {subscription.subscriber_name}: {e}"
                )

        self.logger.debug(
            f"Published message to topic '{topic}', delivered to {delivered} subscribers"
        )
        return delivered

    async def send_direct(self, to_agent: str, message: Message) -> bool:
        """
        Send a message directly to a specific agent.

        Args:
            to_agent: Name of the target agent.
            message: The message to send.

        Returns:
            bool: True if the agent was found and message delivered.
        """
        # Find subscriptions for the agent and deliver to their default handler
        topic = f"agent:{to_agent}"
        subscribers = self._subscriptions.get(topic, [])

        if not subscribers:
            self.logger.warning(f"No subscribers found for agent '{to_agent}'")
            return False

        for subscription in subscribers:
            try:
                await subscription.handler(message)
            except Exception as e:
                self.logger.error(f"Error sending direct message to {to_agent}: {e}")
                return False

        return True

    async def broadcast(self, message: Message) -> int:
        """
        Broadcast a message to all subscribers.

        Args:
            message: The message to broadcast.

        Returns:
            int: Total number of successful deliveries.
        """
        total_delivered = 0
        for topic in self._subscriptions:
            delivered = await self.publish(topic, message)
            total_delivered += delivered
        return total_delivered

    async def _process_messages(self) -> None:
        """
        Background task to process queued messages.

        This runs continuously and processes messages from the queue.
        """
        while self._running:
            try:
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0,
                )
                # Route message based on to_agent field
                if message.to_agent:
                    await self.send_direct(message.to_agent, message)
                self._message_queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error processing message: {e}")

    async def queue_message(self, message: Message) -> None:
        """
        Queue a message for asynchronous processing.

        Args:
            message: The message to queue.
        """
        await self._message_queue.put(message)

    def get_message_history(
        self,
        limit: int = 100,
        topic: str | None = None,
    ) -> list[Message]:
        """
        Get recent message history.

        Args:
            limit: Maximum number of messages to return.
            topic: Optional topic filter.

        Returns:
            List of recent messages.
        """
        messages = self._message_history[-limit:]
        if topic:
            # Filter by topic would require storing topic with message
            # For now, return all messages
            pass
        return messages

    def get_subscription_count(self, topic: str | None = None) -> int:
        """
        Get the number of active subscriptions.

        Args:
            topic: Optional topic to count subscriptions for.

        Returns:
            int: Number of subscriptions.
        """
        if topic:
            return len(self._subscriptions.get(topic, []))
        return sum(len(subs) for subs in self._subscriptions.values())

    def get_topics(self) -> list[str]:
        """
        Get all topics with active subscriptions.

        Returns:
            List of topic names.
        """
        return list(self._subscriptions.keys())
