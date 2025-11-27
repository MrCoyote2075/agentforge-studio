"""
AgentForge Studio - Error Handler Agent.

The Error Handler Agent analyzes errors from other agents,
categorizes them, and decides on appropriate actions.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import Message


class ErrorCategory(str, Enum):
    """Categorization of error types."""

    SYNTAX = "syntax"
    LOGIC = "logic"
    RUNTIME = "runtime"
    API = "api"
    TIMEOUT = "timeout"
    NETWORK = "network"
    UNKNOWN = "unknown"


class ErrorAction(str, Enum):
    """Actions to take in response to errors."""

    RETRY = "retry"
    SKIP = "skip"
    ESCALATE = "escalate"
    ABORT = "abort"
    FIX = "fix"


class ErrorAnalysis:
    """Result of analyzing an error."""

    def __init__(
        self,
        error_message: str,
        category: ErrorCategory,
        action: ErrorAction,
        suggestion: str | None = None,
        retry_count: int = 0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize error analysis result.

        Args:
            error_message: The original error message.
            category: The category of the error.
            action: The recommended action.
            suggestion: Optional suggested fix.
            retry_count: Current retry count.
            max_retries: Maximum allowed retries.
        """
        self.error_message = error_message
        self.category = category
        self.action = action
        self.suggestion = suggestion
        self.retry_count = retry_count
        self.max_retries = max_retries

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "error_message": self.error_message,
            "category": self.category.value,
            "action": self.action.value,
            "suggestion": self.suggestion,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }


class ErrorHandlerAgent(BaseAgent):
    """
    Error Handler Agent that analyzes and handles errors.

    The Error Handler analyzes errors from other agents, categorizes them,
    decides whether to retry, skip, escalate, or abort, and suggests fixes.

    Attributes:
        error_history: History of analyzed errors.
        retry_counts: Tracking retries per error context.

    Example:
        >>> handler = ErrorHandlerAgent()
        >>> analysis = await handler.analyze_error(error_message, context)
    """

    def __init__(
        self,
        name: str = "ErrorHandler",
        model: str = "gemini-pro",
        message_bus: Any | None = None,
    ) -> None:
        """
        Initialize the Error Handler agent.

        Args:
            name: The agent's name. Defaults to 'ErrorHandler'.
            model: The AI model to use. Defaults to 'gemini-pro'.
            message_bus: Reference to the message bus for communication.
        """
        super().__init__(name=name, model=model, message_bus=message_bus)
        self._error_history: list[ErrorAnalysis] = []
        self._retry_counts: dict[str, int] = {}

    async def process(self, message: Message) -> Message:
        """
        Process an error analysis request.

        Args:
            message: The incoming message with error details.

        Returns:
            Message: Response with error analysis.
        """
        await self._set_busy(f"Analyzing error: {message.content[:50]}")

        try:
            # Analyze the error
            analysis = await self.analyze_error(
                error_message=message.content,
                context=message.metadata.get("context", {}) if message.metadata else {},
            )

            response_content = (
                f"Error Analysis:\n"
                f"Category: {analysis.category.value}\n"
                f"Action: {analysis.action.value}\n"
                f"Suggestion: {analysis.suggestion or 'N/A'}"
            )

        except Exception as e:
            self.logger.error(f"Error analysis failed: {e}")
            response_content = f"Error analysis failed: {str(e)}"
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

        await self._log_activity("Sending message", f"To: {to_agent}")
        return True

    async def receive_message(self, message: Message) -> None:
        """
        Handle a received message.

        Args:
            message: The received message.
        """
        await self._log_activity(
            "Received message",
            f"From: {message.from_agent}",
        )

    async def analyze_error(
        self,
        error_message: str,
        context: dict[str, Any] | None = None,
    ) -> ErrorAnalysis:
        """
        Analyze an error and determine the appropriate action.

        Args:
            error_message: The error message to analyze.
            context: Optional context about where the error occurred.

        Returns:
            ErrorAnalysis: The analysis result with recommended action.
        """
        await self._set_busy("Analyzing error")

        # Categorize the error
        category = self._categorize_error(error_message)

        # Get retry count for this context
        context_key = str(context) if context else error_message[:50]
        retry_count = self._retry_counts.get(context_key, 0)

        # Determine action based on category and retry count
        action, suggestion = await self._determine_action(
            error_message, category, retry_count
        )

        # Create analysis result
        analysis = ErrorAnalysis(
            error_message=error_message,
            category=category,
            action=action,
            suggestion=suggestion,
            retry_count=retry_count,
        )

        # Update tracking
        if action == ErrorAction.RETRY:
            self._retry_counts[context_key] = retry_count + 1

        self._error_history.append(analysis)

        await self._set_idle()
        return analysis

    def _categorize_error(self, error_message: str) -> ErrorCategory:
        """
        Categorize an error based on its message.

        Args:
            error_message: The error message to categorize.

        Returns:
            ErrorCategory: The determined error category.
        """
        error_lower = error_message.lower()

        # Syntax errors
        if any(
            kw in error_lower
            for kw in ["syntax", "parse", "unexpected token", "invalid"]
        ):
            return ErrorCategory.SYNTAX

        # API errors
        if any(
            kw in error_lower
            for kw in ["api", "rate limit", "unauthorized", "forbidden", "401", "403"]
        ):
            return ErrorCategory.API

        # Timeout errors
        if any(kw in error_lower for kw in ["timeout", "timed out", "deadline"]):
            return ErrorCategory.TIMEOUT

        # Network errors
        if any(
            kw in error_lower
            for kw in ["network", "connection", "dns", "unreachable"]
        ):
            return ErrorCategory.NETWORK

        # Runtime errors
        if any(
            kw in error_lower
            for kw in [
                "runtime",
                "exception",
                "null",
                "undefined",
                "type error",
                "reference error",
            ]
        ):
            return ErrorCategory.RUNTIME

        # Logic errors
        if any(
            kw in error_lower
            for kw in ["assertion", "expect", "logic", "condition"]
        ):
            return ErrorCategory.LOGIC

        return ErrorCategory.UNKNOWN

    async def _determine_action(
        self,
        error_message: str,
        category: ErrorCategory,
        retry_count: int,
    ) -> tuple[ErrorAction, str | None]:
        """
        Determine the appropriate action for an error.

        Args:
            error_message: The error message.
            category: The error category.
            retry_count: Current retry count.

        Returns:
            tuple: (action, suggestion)
        """
        max_retries = 3

        # If we've exceeded retries, escalate or abort
        if retry_count >= max_retries:
            if category in [ErrorCategory.SYNTAX, ErrorCategory.LOGIC]:
                return ErrorAction.ESCALATE, "Maximum retries exceeded. Needs review."
            return ErrorAction.ABORT, "Maximum retries exceeded. Cannot proceed."

        # Category-specific handling
        if category == ErrorCategory.API:
            if "rate limit" in error_message.lower():
                return ErrorAction.RETRY, "Wait and retry with exponential backoff."
            return ErrorAction.RETRY, "Try a different API key or provider."

        elif category == ErrorCategory.TIMEOUT:
            return ErrorAction.RETRY, "Increase timeout or reduce request size."

        elif category == ErrorCategory.NETWORK:
            return ErrorAction.RETRY, "Check network connection and retry."

        elif category == ErrorCategory.SYNTAX:
            # Try to get AI-powered suggestion
            try:
                suggestion = await self._get_fix_suggestion(error_message)
                return ErrorAction.FIX, suggestion
            except Exception:
                return ErrorAction.ESCALATE, "Syntax error requires manual review."

        elif category == ErrorCategory.LOGIC:
            return ErrorAction.ESCALATE, "Logic error requires investigation."

        elif category == ErrorCategory.RUNTIME:
            return ErrorAction.RETRY, "Check input data and retry."

        return ErrorAction.SKIP, "Unknown error type. Skipping this task."

    async def _get_fix_suggestion(self, error_message: str) -> str:
        """
        Get an AI-powered suggestion to fix an error.

        Args:
            error_message: The error message.

        Returns:
            str: Suggested fix.
        """
        prompt = f"""Analyze this error and suggest a fix:

Error: {error_message}

Provide a concise, actionable suggestion to fix this error.
Focus on the most likely cause and solution."""

        try:
            response = await self.get_ai_response(prompt)
            return response
        except Exception as e:
            self.logger.warning(f"Could not get AI suggestion: {e}")
            return "Review the error message and check related code."

    async def suggest_fix(
        self,
        error_message: str,
        code_context: str | None = None,
    ) -> str:
        """
        Suggest a fix for an error with optional code context.

        Args:
            error_message: The error message.
            code_context: Optional code that caused the error.

        Returns:
            str: Suggested fix.
        """
        await self._set_busy("Generating fix suggestion")

        prompt = f"""Analyze this error and suggest a fix:

Error: {error_message}
"""
        if code_context:
            prompt += f"""
Code context:
```
{code_context}
```
"""

        prompt += """
Provide:
1. What caused this error
2. How to fix it
3. How to prevent it in the future

Be concise and actionable."""

        try:
            suggestion = await self.get_ai_response(prompt)
            await self._set_idle()
            return suggestion
        except Exception as e:
            self.logger.error(f"Fix suggestion failed: {e}")
            await self._set_idle()
            return "Unable to generate fix suggestion. Please review manually."

    async def get_error_history(self) -> list[dict[str, Any]]:
        """
        Get the history of analyzed errors.

        Returns:
            list: List of error analysis dictionaries.
        """
        return [analysis.to_dict() for analysis in self._error_history]

    async def get_error_stats(self) -> dict[str, Any]:
        """
        Get statistics about errors.

        Returns:
            dict: Error statistics.
        """
        category_counts: dict[str, int] = {}
        action_counts: dict[str, int] = {}

        for analysis in self._error_history:
            cat = analysis.category.value
            act = analysis.action.value
            category_counts[cat] = category_counts.get(cat, 0) + 1
            action_counts[act] = action_counts.get(act, 0) + 1

        return {
            "total_errors": len(self._error_history),
            "by_category": category_counts,
            "by_action": action_counts,
            "active_retries": len(self._retry_counts),
        }

    def clear_history(self) -> None:
        """Clear error history and retry counts."""
        self._error_history.clear()
        self._retry_counts.clear()
