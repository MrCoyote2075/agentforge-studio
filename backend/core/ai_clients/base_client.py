"""
AgentForge Studio - Base AI Client.

This module defines the abstract base class for all AI clients.
All provider-specific clients inherit from BaseAIClient.
"""

import asyncio
import logging
from abc import ABC, abstractmethod


class AIClientError(Exception):
    """Exception raised when an AI client encounters an error."""

    def __init__(self, message: str, provider: str, retryable: bool = False) -> None:
        """
        Initialize the AI client error.

        Args:
            message: Error message.
            provider: The AI provider that raised the error.
            retryable: Whether the operation can be retried.
        """
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable


class BaseAIClient(ABC):
    """
    Abstract base class for AI clients.

    This class provides the common interface that all AI provider clients
    must implement, including text generation and code generation methods.

    Attributes:
        provider_name: Name of the AI provider.
        model: The model being used.
        max_retries: Maximum number of retries for failed requests.
        retry_delay: Delay in seconds between retries.
        logger: Logger instance for this client.

    Example:
        >>> class MyAIClient(BaseAIClient):
        ...     async def generate(self, prompt, system_prompt=None, **kwargs):
        ...         return "Generated response"
    """

    def __init__(
        self,
        provider_name: str,
        model: str,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """
        Initialize the base AI client.

        Args:
            provider_name: Name of the AI provider.
            model: The model to use for generation.
            max_retries: Maximum number of retries for failed requests.
            retry_delay: Delay in seconds between retries.
        """
        self.provider_name = provider_name
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(f"ai_client.{provider_name}")

    @abstractmethod
    async def _generate_impl(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> str:
        """
        Internal implementation of text generation.

        This method should be implemented by each provider client.

        Args:
            prompt: The user prompt.
            system_prompt: Optional system prompt for context.
            **kwargs: Additional provider-specific parameters.

        Returns:
            str: The generated text response.

        Raises:
            AIClientError: If generation fails.
        """
        raise NotImplementedError("Subclasses must implement _generate_impl()")

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> str:
        """
        Generate text response from the AI model with automatic retries.

        Args:
            prompt: The user prompt.
            system_prompt: Optional system prompt for context.
            **kwargs: Additional provider-specific parameters.

        Returns:
            str: The generated text response.

        Raises:
            AIClientError: If generation fails after all retries.
        """
        last_error: AIClientError | None = None

        for attempt in range(self.max_retries):
            try:
                self.logger.debug(
                    f"Generation attempt {attempt + 1}/{self.max_retries}"
                )
                return await self._generate_impl(prompt, system_prompt, **kwargs)
            except AIClientError as e:
                last_error = e
                if not e.retryable:
                    self.logger.error(f"Non-retryable error: {e}")
                    raise
                self.logger.warning(
                    f"Attempt {attempt + 1} failed: {e}. Retrying..."
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))

        raise AIClientError(
            f"Generation failed after {self.max_retries} attempts: {last_error}",
            provider=self.provider_name,
            retryable=False,
        )

    async def generate_code(
        self,
        prompt: str,
        language: str = "python",
        **kwargs,
    ) -> str:
        """
        Generate code from the AI model.

        This method wraps the generate method with a code-specific system prompt.

        Args:
            prompt: Description of the code to generate.
            language: Programming language for the generated code.
            **kwargs: Additional provider-specific parameters.

        Returns:
            str: The generated code.

        Raises:
            AIClientError: If code generation fails.
        """
        system_prompt = (
            f"You are an expert {language} programmer. Generate clean, "
            f"well-documented, production-ready {language} code. "
            "Only output the code without explanations or markdown formatting "
            "unless specifically asked. Follow best practices and conventions."
        )

        return await self.generate(prompt, system_prompt=system_prompt, **kwargs)

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the AI client is properly configured and available.

        Returns:
            bool: True if the client can be used, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement is_available()")

    def __repr__(self) -> str:
        """Return a string representation of the client."""
        return (
            f"{self.__class__.__name__}"
            f"(provider='{self.provider_name}', model='{self.model}')"
        )
