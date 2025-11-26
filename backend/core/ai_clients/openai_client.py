"""
AgentForge Studio - OpenAI Client.

This module provides the AI client for OpenAI's API.
"""


from backend.core.ai_clients.base_client import AIClientError, BaseAIClient
from backend.core.config import get_settings


class OpenAIClient(BaseAIClient):
    """
    AI client for OpenAI's API.

    This client wraps the openai package to provide
    text and code generation using GPT models.

    Attributes:
        api_key: The OpenAI API key.
        client: The OpenAI AsyncOpenAI instance.

    Example:
        >>> client = OpenAIClient()
        >>> response = await client.generate("Hello, world!")
    """

    def __init__(
        self,
        model: str = "gpt-4-turbo",
        api_key: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """
        Initialize the OpenAI client.

        Args:
            model: The OpenAI model to use.
            api_key: Optional API key. If not provided, reads from settings.
            max_retries: Maximum number of retries for failed requests.
            retry_delay: Delay in seconds between retries.
        """
        super().__init__(
            provider_name="openai",
            model=model,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )

        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key
        self._client = None

        if self.api_key:
            self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize the OpenAI client with the API key."""
        try:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(api_key=self.api_key)
            self.logger.info(f"OpenAI client initialized with model: {self.model}")
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {e}")
            self._client = None

    async def _generate_impl(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> str:
        """
        Generate text using the OpenAI API.

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
                "OpenAI client not initialized. Check API key.",
                provider=self.provider_name,
                retryable=False,
            )

        try:
            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # Build request parameters
            params = {
                "model": self.model,
                "messages": messages,
            }

            if "temperature" in kwargs:
                params["temperature"] = kwargs["temperature"]
            if "max_tokens" in kwargs:
                params["max_tokens"] = kwargs["max_tokens"]

            # Generate response
            response = await self._client.chat.completions.create(**params)

            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content

            raise AIClientError(
                "Empty response from OpenAI",
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
                f"OpenAI API error: {e}",
                provider=self.provider_name,
                retryable=True,
            )

    def is_available(self) -> bool:
        """
        Check if the OpenAI client is available.

        Returns:
            bool: True if the client is properly configured.
        """
        return bool(self.api_key and self._client)
