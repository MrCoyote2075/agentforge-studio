"""
AgentForge Studio - Anthropic Client.

This module provides the AI client for Anthropic's Claude API.
"""


from backend.core.ai_clients.base_client import AIClientError, BaseAIClient
from backend.core.config import get_settings


class AnthropicClient(BaseAIClient):
    """
    AI client for Anthropic's Claude API.

    This client wraps the anthropic package to provide
    text and code generation using Claude models.

    Attributes:
        api_key: The Anthropic API key.
        client: The Anthropic AsyncAnthropic instance.

    Example:
        >>> client = AnthropicClient()
        >>> response = await client.generate("Hello, world!")
    """

    def __init__(
        self,
        model: str = "claude-3-sonnet-20240229",
        api_key: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """
        Initialize the Anthropic client.

        Args:
            model: The Claude model to use.
            api_key: Optional API key. If not provided, reads from settings.
            max_retries: Maximum number of retries for failed requests.
            retry_delay: Delay in seconds between retries.
        """
        super().__init__(
            provider_name="anthropic",
            model=model,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )

        settings = get_settings()
        self.api_key = api_key or settings.anthropic_api_key
        self._client = None

        if self.api_key:
            self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize the Anthropic client with the API key."""
        try:
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(api_key=self.api_key)
            self.logger.info(f"Anthropic client initialized with model: {self.model}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Anthropic client: {e}")
            self._client = None

    async def _generate_impl(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> str:
        """
        Generate text using the Anthropic API.

        Args:
            prompt: The user prompt.
            system_prompt: Optional system prompt for context.
            **kwargs: Additional parameters (temperature, max_tokens, etc.).

        Returns:
            str: The generated text response.

        Raises:
            AIClientError: If generation fails.
        """
        if not self._client:
            raise AIClientError(
                "Anthropic client not initialized. Check API key.",
                provider=self.provider_name,
                retryable=False,
            )

        try:
            # Build request parameters
            params = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": kwargs.get("max_tokens", 4096),
            }

            if system_prompt:
                params["system"] = system_prompt

            if "temperature" in kwargs:
                params["temperature"] = kwargs["temperature"]

            # Generate response
            response = await self._client.messages.create(**params)

            if response.content and len(response.content) > 0:
                # Get text from the first content block
                content_block = response.content[0]
                if hasattr(content_block, "text"):
                    return content_block.text

            raise AIClientError(
                "Empty response from Anthropic",
                provider=self.provider_name,
                retryable=True,
            )

        except AIClientError:
            raise
        except Exception as e:
            error_message = str(e).lower()
            # Check for rate limiting
            if "rate" in error_message or "429" in error_message:
                raise AIClientError(
                    f"Rate limit exceeded: {e}",
                    provider=self.provider_name,
                    retryable=True,
                )
            # Check for API key issues
            if "api key" in error_message or "401" in error_message:
                raise AIClientError(
                    f"API key error: {e}",
                    provider=self.provider_name,
                    retryable=False,
                )
            # Check for model issues
            if "model" in error_message:
                raise AIClientError(
                    f"Model error: {e}",
                    provider=self.provider_name,
                    retryable=False,
                )
            # Generic error
            raise AIClientError(
                f"Anthropic API error: {e}",
                provider=self.provider_name,
                retryable=True,
            )

    def is_available(self) -> bool:
        """
        Check if the Anthropic client is available.

        Returns:
            bool: True if the client is properly configured.
        """
        return bool(self.api_key and self._client)
