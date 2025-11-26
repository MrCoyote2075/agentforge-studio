"""
AgentForge Studio - Base Agent.

This module defines the abstract base class for all AI agents in the system.
All specialized agents inherit from BaseAgent and implement its abstract methods.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from backend.core.ai_clients.provider_manager import ProviderManager
from backend.models.schemas import AgentStatus, Message


class AgentState(str, Enum):
    """Enumeration of possible agent states."""

    IDLE = "idle"
    BUSY = "busy"
    WAITING = "waiting"
    ERROR = "error"
    OFFLINE = "offline"


# Singleton provider manager for all agents
_provider_manager: ProviderManager | None = None


def get_provider_manager() -> ProviderManager:
    """Get or create the shared provider manager instance."""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager()
    return _provider_manager


class BaseAgent(ABC):
    """
    Abstract base class for all AI agents in AgentForge Studio.

    This class provides the common interface and functionality that all
    specialized agents must implement. It handles message passing, state
    management, AI client integration, and logging.

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

    # Path to prompts directory
    PROMPTS_DIR = Path(__file__).parent / "prompts"

    def __init__(
        self,
        name: str,
        model: str = "gemini-pro",
        message_bus: Any | None = None,
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
        self._current_task: str | None = None
        self._created_at = datetime.utcnow()
        self.logger = logging.getLogger(f"agent.{name}")
        self._system_prompt: str | None = None
        self._load_system_prompt()

    def _load_system_prompt(self) -> None:
        """Load the system prompt from the prompts directory."""
        # Convert agent name to prompt filename
        prompt_name = self._name.lower().replace(" ", "_")
        prompt_file = self.PROMPTS_DIR / f"{prompt_name}_prompt.txt"

        if prompt_file.exists():
            try:
                self._system_prompt = prompt_file.read_text(encoding="utf-8")
                self.logger.debug(f"Loaded system prompt from {prompt_file}")
            except Exception as e:
                self.logger.warning(f"Failed to load system prompt: {e}")
                self._system_prompt = None
        else:
            self.logger.debug(f"No system prompt file found at {prompt_file}")

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
    def message_bus(self) -> Any | None:
        """Get the message bus reference."""
        return self._message_bus

    @message_bus.setter
    def message_bus(self, value: Any) -> None:
        """Set the message bus reference."""
        self._message_bus = value

    @property
    def current_task(self) -> str | None:
        """Get the current task being processed."""
        return self._current_task

    @property
    def system_prompt(self) -> str | None:
        """Get the agent's system prompt."""
        return self._system_prompt

    @property
    def ai_client(self) -> ProviderManager:
        """Get the shared AI provider manager."""
        return get_provider_manager()

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

    async def get_ai_response(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> str:
        """
        Get a response from the AI using the configured provider.

        Args:
            prompt: The user prompt.
            system_prompt: Optional system prompt. If not provided,
                           uses the agent's default system prompt.
            **kwargs: Additional parameters for generation.

        Returns:
            str: The AI-generated response.

        Raises:
            AIClientError: If generation fails.
        """
        # Use agent's system prompt if none provided
        effective_system_prompt = system_prompt or self._system_prompt

        try:
            response, provider = await self.ai_client.generate(
                prompt=prompt,
                system_prompt=effective_system_prompt,
                **kwargs,
            )
            self.logger.debug(f"Generated response using {provider}")
            return response
        except Exception as e:
            self.logger.error(f"AI generation failed: {e}")
            raise

    async def generate_code(
        self,
        prompt: str,
        language: str = "python",
        **kwargs,
    ) -> str:
        """
        Generate code using the AI.

        Args:
            prompt: Description of the code to generate.
            language: Programming language.
            **kwargs: Additional parameters.

        Returns:
            str: The generated code.

        Raises:
            AIClientError: If generation fails.
        """
        try:
            code, provider = await self.ai_client.generate_code(
                prompt=prompt,
                language=language,
                **kwargs,
            )
            self.logger.debug(f"Generated code using {provider}")
            return code
        except Exception as e:
            self.logger.error(f"Code generation failed: {e}")
            raise

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
        raise NotImplementedError("Subclasses must implement receive_message()")

    async def _log_activity(self, action: str, details: str | None = None) -> None:
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

    async def _set_error(self, error: str) -> None:
        """Set the agent to error status."""
        self._status = AgentState.ERROR
        await self._log_activity("Error occurred", error)

    @staticmethod
    def _clean_code_response(response: str, language: str = "") -> str:
        """
        Clean markdown code blocks from an AI response.

        Args:
            response: The raw AI response that may contain code blocks.
            language: Optional language hint for the code block.

        Returns:
            str: The cleaned code without markdown formatting.
        """
        clean = response.strip()
        # Remove language-specific markdown code blocks
        if language:
            prefix = f"```{language}"
            if clean.startswith(prefix):
                clean = clean[len(prefix):]
        # Remove generic markdown code blocks
        if clean.startswith("```"):
            # Find the first newline to skip the language tag if any
            first_newline = clean.find("\n")
            if first_newline != -1:
                clean = clean[first_newline + 1:]
            else:
                clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        return clean.strip()

    def __repr__(self) -> str:
        """Return a string representation of the agent."""
        return (
            f"{self.__class__.__name__}"
            f"(name='{self._name}', status='{self._status.value}')"
        )
