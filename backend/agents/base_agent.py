"""
Base Agent module for AgentForge Studio.

This module provides the abstract base class for all specialized agents
in the system.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class AgentStatus(Enum):
    """Enumeration of possible agent states."""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class AgentMessage:
    """
    Data class representing a message between agents.
    
    Attributes:
        id: Unique identifier for the message.
        sender: Name of the sending agent.
        recipient: Name of the receiving agent.
        content: Message content/payload.
        timestamp: When the message was created.
        metadata: Additional message metadata.
    """
    sender: str
    recipient: str
    content: Any
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the system.
    
    Provides common functionality and interface that all specialized
    agents must implement.
    
    Attributes:
        name: The unique name of the agent.
        description: A brief description of the agent's purpose.
        status: Current status of the agent.
    """
    
    def __init__(
        self,
        name: str,
        description: str = "",
        config: Optional[dict[str, Any]] = None
    ) -> None:
        """
        Initialize the base agent.
        
        Args:
            name: Unique name for the agent.
            description: Brief description of agent's purpose.
            config: Optional configuration dictionary.
        """
        self.name = name
        self.description = description
        self.config = config or {}
        self._status = AgentStatus.IDLE
        self._message_history: list[AgentMessage] = []
    
    @property
    def status(self) -> AgentStatus:
        """Get the current status of the agent."""
        return self._status
    
    @status.setter
    def status(self, value: AgentStatus) -> None:
        """Set the status of the agent."""
        self._status = value
    
    @abstractmethod
    async def process(self, message: AgentMessage) -> AgentMessage:
        """
        Process an incoming message and return a response.
        
        Args:
            message: The incoming message to process.
            
        Returns:
            The response message from the agent.
        """
        pass
    
    @abstractmethod
    async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a task and return the result.
        
        Args:
            task: The task definition to execute.
            
        Returns:
            The result of the task execution.
        """
        pass
    
    def add_to_history(self, message: AgentMessage) -> None:
        """
        Add a message to the agent's message history.
        
        Args:
            message: The message to add to history.
        """
        self._message_history.append(message)
    
    def get_history(self) -> list[AgentMessage]:
        """
        Get the agent's message history.
        
        Returns:
            List of messages in the agent's history.
        """
        return self._message_history.copy()
    
    def clear_history(self) -> None:
        """Clear the agent's message history."""
        self._message_history.clear()
    
    def __repr__(self) -> str:
        """Return string representation of the agent."""
        return f"{self.__class__.__name__}(name='{self.name}', status={self.status.value})"
