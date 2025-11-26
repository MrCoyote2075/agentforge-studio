"""
AgentForge Studio - Intermediator Agent.

The Intermediator is the single point of contact between human clients
and the AI agent team. It translates user requirements into technical
specifications and provides user-friendly progress updates.
"""

from datetime import datetime
from typing import Any, List, Optional

from backend.agents.base_agent import BaseAgent, AgentState
from backend.models.schemas import Message, ChatMessage


class Intermediator(BaseAgent):
    """
    Intermediator agent that serves as the client liaison.

    The Intermediator is the only agent that directly communicates with
    human users. It translates natural language requirements into
    structured specifications for other agents and presents technical
    progress in user-friendly terms.

    Attributes:
        conversation_history: List of previous chat messages.
        current_project_id: ID of the current active project.

    Example:
        >>> intermediator = Intermediator()
        >>> response = await intermediator.chat("Build me a landing page")
    """

    def __init__(
        self,
        name: str = "Intermediator",
        model: str = "gemini-pro",
        message_bus: Optional[Any] = None,
    ) -> None:
        """
        Initialize the Intermediator agent.

        Args:
            name: The agent's name. Defaults to 'Intermediator'.
            model: The AI model to use. Defaults to 'gemini-pro'.
            message_bus: Reference to the message bus for communication.
        """
        super().__init__(name=name, model=model, message_bus=message_bus)
        self._conversation_history: List[ChatMessage] = []
        self._current_project_id: Optional[str] = None

    @property
    def conversation_history(self) -> List[ChatMessage]:
        """Get the conversation history."""
        return self._conversation_history

    @property
    def current_project_id(self) -> Optional[str]:
        """Get the current project ID."""
        return self._current_project_id

    async def process(self, message: Message) -> Message:
        """
        Process an incoming message from the client or other agents.

        For client messages, translates requirements and forwards to Orchestrator.
        For agent messages, translates progress into user-friendly updates.

        Args:
            message: The incoming message to process.

        Returns:
            Message: Response message for the sender.
        """
        await self._set_busy(f"Processing message from {message.from_agent}")

        # TODO: Implement AI-powered message processing
        # 1. Determine if message is from client or agent
        # 2. For client: translate requirements and forward to Orchestrator
        # 3. For agent: translate technical updates for client

        response_content = (
            f"I've received your request and am coordinating with the team. "
            f"Summary: {message.content[:100]}..."
        )

        await self._set_idle()

        return Message(
            from_agent=self.name,
            to_agent=message.from_agent,
            content=response_content,
            message_type="response",
            timestamp=datetime.utcnow(),
        )

    async def send_message(
        self,
        to_agent: str,
        content: str,
        message_type: str = "request",
    ) -> bool:
        """
        Send a message to another agent.

        Args:
            to_agent: Target agent name.
            content: Message content.
            message_type: Type of message.

        Returns:
            bool: True if sent successfully.
        """
        if not self._message_bus:
            self.logger.warning("No message bus configured")
            return False

        message = Message(
            from_agent=self.name,
            to_agent=to_agent,
            content=content,
            message_type=message_type,
            timestamp=datetime.utcnow(),
        )

        # TODO: Implement actual message bus publishing
        await self._log_activity("Sending message", f"To: {to_agent}")
        return True

    async def receive_message(self, message: Message) -> None:
        """
        Handle a received message from another agent.

        Args:
            message: The received message.
        """
        await self._log_activity(
            "Received message",
            f"From: {message.from_agent}, Type: {message.message_type}",
        )
        # TODO: Implement message handling and client notification

    async def chat(self, user_message: str, project_id: Optional[str] = None) -> str:
        """
        Handle a chat message from the user.

        This is the main entry point for user interaction. It processes
        the user's natural language input and returns a friendly response
        while coordinating with other agents behind the scenes.

        Args:
            user_message: The message from the user.
            project_id: Optional project ID to associate with the message.

        Returns:
            str: The response to show the user.
        """
        await self._set_busy("Processing user chat")

        # Store in conversation history
        chat_message = ChatMessage(
            content=user_message,
            project_id=project_id,
            role="user",
        )
        self._conversation_history.append(chat_message)

        if project_id:
            self._current_project_id = project_id

        # TODO: Implement AI-powered chat response
        # 1. Analyze user intent
        # 2. Extract requirements or questions
        # 3. Coordinate with Orchestrator if needed
        # 4. Generate friendly response

        response = (
            f"Thanks for your message! I understand you want: '{user_message[:50]}...'. "
            "Let me coordinate with the team to get this done."
        )

        # Store assistant response
        assistant_message = ChatMessage(
            content=response,
            project_id=project_id,
            role="assistant",
        )
        self._conversation_history.append(assistant_message)

        await self._set_idle()
        return response

    async def get_progress_update(self) -> str:
        """
        Get a user-friendly progress update on the current project.

        Returns:
            str: A friendly description of current progress.
        """
        # TODO: Query Orchestrator for actual progress
        return "Your project is progressing well. The team is working on it!"

    async def translate_requirements(self, user_input: str) -> dict:
        """
        Translate user requirements into technical specifications.

        Args:
            user_input: Natural language requirements from the user.

        Returns:
            dict: Structured technical specifications.
        """
        # TODO: Implement AI-powered requirement extraction
        await self._log_activity("Translating requirements", user_input[:50])
        return {
            "raw_input": user_input,
            "extracted_features": [],
            "technical_requirements": [],
        }

    async def format_update_for_user(self, technical_update: str) -> str:
        """
        Format a technical update into user-friendly language.

        Args:
            technical_update: Technical progress information.

        Returns:
            str: User-friendly version of the update.
        """
        # TODO: Implement AI-powered translation
        return f"Update: {technical_update}"
