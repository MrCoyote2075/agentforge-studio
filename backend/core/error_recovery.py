"""
AgentForge Studio - Error Recovery.

This module implements error recovery strategies for handling
different types of errors with appropriate actions.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any

from backend.core.loop_detector import LoopDetector


class RecoveryAction(str, Enum):
    """Actions that can be taken to recover from errors."""

    RETRY = "retry"
    SKIP = "skip"
    ESCALATE = "escalate"
    ABORT = "abort"
    ALTERNATIVE = "alternative"


class ErrorType(str, Enum):
    """Categories of errors for recovery handling."""

    TRANSIENT = "transient"  # Temporary failures that may succeed on retry
    RATE_LIMIT = "rate_limit"  # API rate limiting
    AUTHENTICATION = "authentication"  # Auth failures
    VALIDATION = "validation"  # Input validation errors
    TIMEOUT = "timeout"  # Operation timeouts
    RESOURCE = "resource"  # Resource unavailable
    LOGIC = "logic"  # Logic/programming errors
    UNKNOWN = "unknown"  # Unclassified errors


class RecoveryResult:
    """Result of an error recovery attempt."""

    def __init__(
        self,
        action: RecoveryAction,
        message: str,
        modified_context: dict[str, Any] | None = None,
        delay_seconds: float = 0.0,
        error_type: ErrorType = ErrorType.UNKNOWN,
    ) -> None:
        """
        Initialize RecoveryResult.

        Args:
            action: The action to take.
            message: Explanation of the action.
            modified_context: Changes for retry attempts.
            delay_seconds: Recommended delay before retry.
            error_type: The classified error type.
        """
        self.action = action
        self.message = message
        self.modified_context = modified_context or {}
        self.delay_seconds = delay_seconds
        self.error_type = error_type
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "action": self.action.value,
            "message": self.message,
            "modified_context": self.modified_context,
            "delay_seconds": self.delay_seconds,
            "error_type": self.error_type.value,
            "timestamp": self.timestamp.isoformat(),
        }


class ErrorRecovery:
    """
    Handles error recovery using various strategies.

    Works with LoopDetector to prevent infinite retries and
    optionally uses ErrorHandlerAgent for complex recovery.

    Attributes:
        loop_detector: Detector for preventing infinite loops.
        error_handler_agent: Optional agent for complex recovery.
        recovery_history: History of recovery attempts.
        logger: Logger instance.

    Example:
        >>> recovery = ErrorRecovery(LoopDetector())
        >>> result = await recovery.handle_error(error, {"task_id": "t1"})
        >>> if result.action == RecoveryAction.RETRY:
        ...     # Retry the operation
        ...     pass
    """

    def __init__(
        self,
        loop_detector: LoopDetector,
        error_handler_agent: Any | None = None,
    ) -> None:
        """
        Initialize ErrorRecovery.

        Args:
            loop_detector: LoopDetector instance for retry tracking.
            error_handler_agent: Optional ErrorHandlerAgent for complex recovery.
        """
        self.loop_detector = loop_detector
        self.error_handler_agent = error_handler_agent
        self._recovery_history: list[dict[str, Any]] = []
        self.logger = logging.getLogger("error_recovery")

    async def handle_error(
        self,
        error: Exception,
        context: dict[str, Any],
    ) -> RecoveryResult:
        """
        Handle an error and determine recovery action.

        Args:
            error: The exception that occurred.
            context: Context about the operation that failed.

        Returns:
            RecoveryResult with action and recommendations.
        """
        task_id = context.get("task_id", str(id(error)))
        error_type = self._classify_error(error)

        self.logger.info(
            f"Handling {error_type.value} error for task {task_id}: {error}"
        )

        # Record the attempt
        attempt_count = self.loop_detector.record_attempt(task_id)
        can_retry = self.loop_detector.should_retry(task_id)

        # Determine action based on error type and retry status
        result = await self._determine_action(
            error=error,
            error_type=error_type,
            task_id=task_id,
            context=context,
            attempt_count=attempt_count,
            can_retry=can_retry,
        )

        # Record in history
        self._record_recovery(task_id, error, result)

        return result

    def _classify_error(self, error: Exception) -> ErrorType:
        """
        Classify an error into an error type.

        Args:
            error: The exception to classify.

        Returns:
            The classified ErrorType.
        """
        error_str = str(error).lower()
        error_type_name = type(error).__name__.lower()

        # Check for specific error types
        if any(kw in error_str for kw in ["rate limit", "429", "too many requests"]):
            return ErrorType.RATE_LIMIT

        if any(kw in error_str for kw in ["timeout", "timed out", "deadline"]):
            return ErrorType.TIMEOUT

        if any(
            kw in error_str
            for kw in ["unauthorized", "forbidden", "401", "403", "authentication"]
        ):
            return ErrorType.AUTHENTICATION

        if any(
            kw in error_str
            for kw in ["validation", "invalid", "required field", "schema"]
        ):
            return ErrorType.VALIDATION

        if any(
            kw in error_str
            for kw in ["not found", "unavailable", "503", "500", "resource"]
        ):
            return ErrorType.RESOURCE

        if any(
            kw in error_type_name
            for kw in ["connection", "network", "socket", "dns"]
        ):
            return ErrorType.TRANSIENT

        if any(
            kw in error_str
            for kw in ["assertion", "logic", "index", "key error", "attribute"]
        ):
            return ErrorType.LOGIC

        return ErrorType.UNKNOWN

    async def _determine_action(
        self,
        error: Exception,
        error_type: ErrorType,
        task_id: str,
        context: dict[str, Any],
        attempt_count: int,
        can_retry: bool,
    ) -> RecoveryResult:
        """
        Determine the recovery action for an error.

        Args:
            error: The exception.
            error_type: Classified error type.
            task_id: Task identifier.
            context: Operation context.
            attempt_count: Number of attempts.
            can_retry: Whether retries are allowed.

        Returns:
            RecoveryResult with recommended action.
        """
        # If we've exceeded retries, escalate
        if not can_retry:
            return await self._handle_exceeded_retries(
                error, error_type, task_id, context
            )

        # Handle based on error type
        if error_type == ErrorType.RATE_LIMIT:
            delay = min(60 * (2 ** (attempt_count - 1)), 300)  # Exponential backoff
            return RecoveryResult(
                action=RecoveryAction.RETRY,
                message=(
                    f"Rate limited. Retrying after {delay}s "
                    f"(attempt {attempt_count})"
                ),
                delay_seconds=delay,
                error_type=error_type,
            )

        elif error_type == ErrorType.TIMEOUT:
            return RecoveryResult(
                action=RecoveryAction.RETRY,
                message=f"Timeout. Retrying (attempt {attempt_count})",
                modified_context={"increase_timeout": True},
                delay_seconds=5.0,
                error_type=error_type,
            )

        elif error_type == ErrorType.TRANSIENT:
            return RecoveryResult(
                action=RecoveryAction.RETRY,
                message=f"Transient error. Retrying (attempt {attempt_count})",
                delay_seconds=2.0 * attempt_count,
                error_type=error_type,
            )

        elif error_type == ErrorType.AUTHENTICATION:
            return RecoveryResult(
                action=RecoveryAction.ESCALATE,
                message="Authentication error. Requires manual intervention.",
                error_type=error_type,
            )

        elif error_type == ErrorType.VALIDATION:
            # Try to get alternative approach
            if self.error_handler_agent:
                return await self.try_alternative_approach(
                    {"task_id": task_id, **context},
                    {"error": str(error), "type": error_type.value},
                )
            return RecoveryResult(
                action=RecoveryAction.SKIP,
                message="Validation error. Skipping task.",
                error_type=error_type,
            )

        elif error_type == ErrorType.RESOURCE:
            return RecoveryResult(
                action=RecoveryAction.RETRY,
                message=f"Resource unavailable. Retrying (attempt {attempt_count})",
                delay_seconds=10.0,
                error_type=error_type,
            )

        elif error_type == ErrorType.LOGIC:
            return RecoveryResult(
                action=RecoveryAction.ESCALATE,
                message="Logic error. Requires investigation.",
                error_type=error_type,
            )

        # Unknown error - try retry first, then escalate
        if attempt_count == 1:
            return RecoveryResult(
                action=RecoveryAction.RETRY,
                message=f"Unknown error. Retrying (attempt {attempt_count})",
                delay_seconds=5.0,
                error_type=error_type,
            )

        return RecoveryResult(
            action=RecoveryAction.ESCALATE,
            message="Unknown error persists. Escalating.",
            error_type=error_type,
        )

    async def _handle_exceeded_retries(
        self,
        error: Exception,
        error_type: ErrorType,
        task_id: str,
        context: dict[str, Any],
    ) -> RecoveryResult:
        """
        Handle case when max retries have been exceeded.

        Args:
            error: The exception.
            error_type: Classified error type.
            task_id: Task identifier.
            context: Operation context.

        Returns:
            RecoveryResult with escalation or abort action.
        """
        self.logger.warning(
            f"Task {task_id} exceeded max retries. Error type: {error_type.value}"
        )

        # Try to get alternative approach from ErrorHandlerAgent
        if self.error_handler_agent:
            try:
                alternative = await self.try_alternative_approach(
                    {"task_id": task_id, **context},
                    {"error": str(error), "type": error_type.value},
                )
                if alternative.action == RecoveryAction.ALTERNATIVE:
                    # Reset loop detector for the new approach
                    self.loop_detector.reset(task_id)
                    return alternative
            except Exception as e:
                self.logger.error(f"Failed to get alternative approach: {e}")

        # Escalate or abort based on error type
        if error_type in [ErrorType.LOGIC, ErrorType.AUTHENTICATION]:
            return RecoveryResult(
                action=RecoveryAction.ABORT,
                message=(
                    f"Max retries exceeded. Cannot continue "
                    f"due to {error_type.value} error."
                ),
                error_type=error_type,
            )

        return RecoveryResult(
            action=RecoveryAction.ESCALATE,
            message=f"Max retries exceeded. Escalating {error_type.value} error.",
            error_type=error_type,
        )

    async def try_alternative_approach(
        self,
        task: dict[str, Any],
        error: dict[str, Any],
    ) -> RecoveryResult:
        """
        Get alternative approach from ErrorHandlerAgent.

        Args:
            task: Task details.
            error: Error details.

        Returns:
            RecoveryResult with alternative approach or escalation.
        """
        if not self.error_handler_agent:
            return RecoveryResult(
                action=RecoveryAction.ESCALATE,
                message="No ErrorHandlerAgent available for alternative approach.",
                error_type=ErrorType.UNKNOWN,
            )

        try:
            from backend.models.schemas import Message

            msg = Message(
                from_agent="ErrorRecovery",
                to_agent="ErrorHandler",
                content=f"Find alternative approach for task {task.get('task_id')}",
                message_type="request",
                metadata={"task": task, "error": error},
            )

            response = await self.error_handler_agent.process(msg)

            return RecoveryResult(
                action=RecoveryAction.ALTERNATIVE,
                message=f"Alternative approach: {response.content[:200]}",
                modified_context={"alternative_approach": response.content},
                error_type=ErrorType(error.get("type", "unknown")),
            )

        except Exception as e:
            self.logger.error(f"ErrorHandlerAgent failed: {e}")
            return RecoveryResult(
                action=RecoveryAction.ESCALATE,
                message=f"Failed to get alternative approach: {e}",
                error_type=ErrorType.UNKNOWN,
            )

    def _record_recovery(
        self,
        task_id: str,
        error: Exception,
        result: RecoveryResult,
    ) -> None:
        """
        Record a recovery attempt in history.

        Args:
            task_id: Task identifier.
            error: The exception.
            result: The recovery result.
        """
        self._recovery_history.append({
            "task_id": task_id,
            "error_type": type(error).__name__,
            "error_message": str(error)[:500],
            "action": result.action.value,
            "message": result.message,
            "timestamp": result.timestamp.isoformat(),
        })

    def mark_success(self, task_id: str) -> None:
        """
        Mark a task as successful (reset retry counter).

        Args:
            task_id: Task identifier.
        """
        self.loop_detector.reset(task_id)
        self.logger.debug(f"Marked task {task_id} as successful")

    def get_recovery_history(self) -> list[dict[str, Any]]:
        """
        Get the history of recovery attempts.

        Returns:
            List of recovery attempt records.
        """
        return list(self._recovery_history)

    def get_stats(self) -> dict[str, Any]:
        """
        Get error recovery statistics.

        Returns:
            Dictionary with recovery statistics.
        """
        action_counts: dict[str, int] = {}
        error_type_counts: dict[str, int] = {}

        for record in self._recovery_history:
            action = record["action"]
            action_counts[action] = action_counts.get(action, 0) + 1

            error_type = record["error_type"]
            error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1

        return {
            "total_recoveries": len(self._recovery_history),
            "by_action": action_counts,
            "by_error_type": error_type_counts,
            "loop_detector_stats": self.loop_detector.get_stats(),
        }

    def clear_history(self) -> None:
        """Clear recovery history."""
        self._recovery_history.clear()
        self.logger.debug("Cleared recovery history")
