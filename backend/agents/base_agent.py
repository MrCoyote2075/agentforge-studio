"""
AgentForge Studio - Base Agent.

This module defines the abstract base class for all AI agents in the system.
All specialized agents inherit from BaseAgent and implement its abstract methods.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import logging

from backend.models.schemas import Message, AgentStatus


class AgentState(str, Enum):
    """Enumeration of possible agent states."""

    IDLE = "idle"
    BUSY = "busy"
    WAITING = "waiting"
    ERROR = "error"
    OFFLINE = "offline"


class BaseAgent(ABC):
    """
    Abstract base class for all AI agents in AgentForge Studio.

    This class provides the common interface and functionality that all
    specialized agents must implement. It handles message passing, state
    management, and logging.

    Attributes:
        name: The unique name identifier for this agent.
        model: The AI model used by this agent (e.g., 'gemini-pro', 'gpt-4').
        status: The current operational status of the agent.
        message_bus: Reference to the message bus for inter-agent communication.
        logger: Logger instance for this agent.

    Example:
        >>> class MyAgent(BaseAgent):
        ...     async def process(self, message):
        ...         return f"Processed: {message.content}"
    """

    def __init__(
        self,
        name: str,
        model: str = "gemini-pro",
        message_bus: Optional[Any] = None,
    ) -> None:
        """
        Initialize the base agent.

        Args:
            name: The unique name identifier for this agent.
            model: The AI model to use for processing. Defaults to 'gemini-pro'.
            message_bus: Reference to the message bus for communication.
        """
        self._name = name
        self._model = model
        self._status = AgentState.IDLE
        self._message_bus = message_bus
        self._current_task: Optional[str] = None
        self._created_at = datetime.utcnow()
        self.logger = logging.getLogger(f"agent.{name}")

    @property
    def name(self) -> str:
        """Get the agent's name."""
        return self._name

    @property
    def model(self) -> str:
        """Get the agent's AI model."""
        return self._model

    @property
    def status(self) -> AgentState:
        """Get the agent's current status."""
        return self._status

    @status.setter
    def status(self, value: AgentState) -> None:
        """Set the agent's status."""
        self._status = value
        self.logger.info(f"Status changed to: {value}")

    @property
    def message_bus(self) -> Optional[Any]:
        """Get the message bus reference."""
        return self._message_bus

    @message_bus.setter
    def message_bus(self, value: Any) -> None:
        """Set the message bus reference."""
        self._message_bus = value

    @property
    def current_task(self) -> Optional[str]:
        """Get the current task being processed."""
        return self._current_task

    def get_status(self) -> AgentStatus:
        """
        Get the agent's status as a Pydantic model.

        Returns:
            AgentStatus: The current status of the agent.
        """
        return AgentStatus(
            name=self._name,
            status=self._status.value,
            current_task=self._current_task,
        )

    @abstractmethod
    async def process(self, message: Message) -> Message:
        """
        Process an incoming message and generate a response.

        This is the main method that child agents must implement to define
        their specific behavior and processing logic.

        Args:
            message: The incoming message to process.

        Returns:
            Message: The response message after processing.

        Raises:
            NotImplementedError: If the child class doesn't implement this method.
        """
        # TODO: Implement in child classes
        raise NotImplementedError("Subclasses must implement process()")

    @abstractmethod
    async def send_message(
        self,
        to_agent: str,
        content: str,
        message_type: str = "request",
    ) -> bool:
        """
        Send a message to another agent via the message bus.

        Args:
            to_agent: The name of the target agent.
            content: The message content to send.
            message_type: Type of message (request, response, notification).

        Returns:
            bool: True if the message was sent successfully, False otherwise.

        Raises:
            NotImplementedError: If the child class doesn't implement this method.
        """
        # TODO: Implement in child classes
        raise NotImplementedError("Subclasses must implement send_message()")

    @abstractmethod
    async def receive_message(self, message: Message) -> None:
        """
        Handle a received message from another agent.

        This method is called by the message bus when a message is
        delivered to this agent.

        Args:
            message: The received message to handle.

        Raises:
            NotImplementedError: If the child class doesn't implement this method.
        """
        # TODO: Implement in child classes
        raise NotImplementedError("Subclasses must implement receive_message()")

    async def _log_activity(self, action: str, details: Optional[str] = None) -> None:
        """
        Log agent activity for debugging and monitoring.

        Args:
            action: The action being performed.
            details: Optional additional details about the action.
        """
        log_message = f"[{self._name}] {action}"
        if details:
            log_message += f": {details}"
        self.logger.info(log_message)

    async def _set_busy(self, task: str) -> None:
        """
        Set the agent to busy status with a specific task.

        Args:
            task: Description of the current task.
        """
        self._status = AgentState.BUSY
        self._current_task = task
        await self._log_activity("Started task", task)

    async def _set_idle(self) -> None:
        """Set the agent to idle status after completing a task."""
        previous_task = self._current_task
        self._status = AgentState.IDLE
        self._current_task = None
        if previous_task:
            await self._log_activity("Completed task", previous_task)

    def __repr__(self) -> str:
        """Return a string representation of the agent."""
        return f"{self.__class__.__name__}(name='{self._name}', status='{self._status.value}')"
