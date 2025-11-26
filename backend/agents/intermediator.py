"""
AgentForge Studio - Intermediator Agent.

The Intermediator is the single point of contact between human clients
and the AI agent team. It translates user requirements into technical
specifications and provides user-friendly progress updates.
"""

from datetime import datetime
from typing import Any

from backend.agents.base_agent import BaseAgent
from backend.core.ai_clients.base_client import AIClientError
from backend.models.schemas import ChatMessage, Message


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
        message_bus: Any | None = None,
    ) -> None:
        """
        Initialize the Intermediator agent.

        Args:
            name: The agent's name. Defaults to 'Intermediator'.
            model: The AI model to use. Defaults to 'gemini-pro'.
            message_bus: Reference to the message bus for communication.
        """
        super().__init__(name=name, model=model, message_bus=message_bus)
        self._conversation_history: list[ChatMessage] = []
        self._current_project_id: str | None = None

    @property
    def conversation_history(self) -> list[ChatMessage]:
        """Get the conversation history."""
        return self._conversation_history

    @property
    def current_project_id(self) -> str | None:
        """Get the current project ID."""
        return self._current_project_id

    def _build_conversation_context(self) -> str:
        """Build conversation context from history for AI."""
        if not self._conversation_history:
            return ""

        context_parts = ["Previous conversation:"]
        # Include last 10 messages for context
        recent_history = self._conversation_history[-10:]
        for msg in recent_history:
            role = "User" if msg.role == "user" else "Assistant"
            context_parts.append(f"{role}: {msg.content}")

        return "\n".join(context_parts)

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

        try:
            # Build prompt with context
            context = self._build_conversation_context()
            prompt = f"{context}\n\nNew message: {message.content}"

            # Get AI response
            response_content = await self.get_ai_response(prompt)

        except AIClientError as e:
            self.logger.error(f"AI generation failed: {e}")
            response_content = (
                "I apologize, but I'm having trouble processing your request "
                "right now. Please try again in a moment."
            )
            await self._set_error(str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            response_content = (
                "I encountered an unexpected error. Please try again."
            )
            await self._set_error(str(e))

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

    async def chat(self, user_message: str, project_id: str | None = None) -> str:
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

        try:
            # Build context from conversation history
            context = self._build_conversation_context()

            # Create prompt for AI
            if len(self._conversation_history) == 1:
                # First message - greet and ask about project
                prompt = f"""The user just started a conversation with this message:

"{user_message}"

Greet them warmly and start gathering requirements. Ask about:
- What type of website/project they want to build
- Any specific features they need
- Their design preferences

Keep your response friendly and concise."""
            else:
                # Continuing conversation
                prompt = f"""{context}

User's new message: "{user_message}"

Continue the conversation naturally. If you have enough information about their project requirements, summarize what you understand and ask if they'd like to proceed. Otherwise, ask clarifying questions about:
- Website type, pages needed, design preferences, features, content needs

Keep responses friendly, helpful, and concise."""

            # Get AI response
            response = await self.get_ai_response(prompt)

        except AIClientError as e:
            self.logger.error(f"AI chat generation failed: {e}")
            response = (
                "I apologize, but I'm having trouble connecting right now. "
                "Please try again in a moment. In the meantime, feel free to "
                "describe what you'd like to build!"
            )
        except Exception as e:
            self.logger.error(f"Unexpected chat error: {e}")
            response = (
                "I encountered an unexpected issue. Please try again, "
                "and I'll do my best to help you with your project."
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
        await self._log_activity("Translating requirements", user_input[:50])

        try:
            prompt = f"""Analyze the following user requirements and extract structured information:

"{user_input}"

Extract and return a JSON object with:
- website_type: The type of website (portfolio, business, landing, etc.)
- pages: List of pages needed
- features: List of features requested
- design_preferences: Any design preferences mentioned
- content_notes: Notes about content they have or need

Return only valid JSON, no additional text."""

            response = await self.get_ai_response(prompt)

            # Try to parse as JSON
            import json

            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {
                    "raw_input": user_input,
                    "extracted_features": [],
                    "technical_requirements": [],
                    "parse_error": "Could not parse AI response as JSON",
                }

        except Exception as e:
            self.logger.error(f"Failed to translate requirements: {e}")
            return {
                "raw_input": user_input,
                "extracted_features": [],
                "technical_requirements": [],
                "error": str(e),
            }

    async def format_update_for_user(self, technical_update: str) -> str:
        """
        Format a technical update into user-friendly language.

        Args:
            technical_update: Technical progress information.

        Returns:
            str: User-friendly version of the update.
        """
        try:
            prompt = f"""Convert this technical update into friendly, non-technical language for a client:

Technical update: "{technical_update}"

Keep it brief, positive, and easy to understand. Don't use technical jargon."""

            return await self.get_ai_response(prompt)

        except Exception as e:
            self.logger.error(f"Failed to format update: {e}")
            return f"Update: {technical_update}"

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self._conversation_history = []
        self._current_project_id = None
