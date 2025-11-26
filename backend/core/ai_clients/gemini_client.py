"""
AgentForge Studio - Gemini AI Client.

This module provides the AI client for Google's Gemini API.
"""


from backend.core.ai_clients.base_client import AIClientError, BaseAIClient
from backend.core.config import get_settings


class GeminiClient(BaseAIClient):
    """
    AI client for Google's Gemini API.

    This client wraps the google-generativeai package to provide
    text and code generation using Gemini models.

    Attributes:
        api_key: The Gemini API key.
        client: The Gemini GenerativeModel instance.

    Example:
        >>> client = GeminiClient()
        >>> response = await client.generate("Hello, world!")
    """

    def __init__(
        self,
        model: str = "gemini-1.5-pro",
        api_key: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """
        Initialize the Gemini client.

        Args:
            model: The Gemini model to use.
            api_key: Optional API key. If not provided, reads from settings.
            max_retries: Maximum number of retries for failed requests.
            retry_delay: Delay in seconds between retries.
        """
        super().__init__(
            provider_name="gemini",
            model=model,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )

        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self._client = None

        if self.api_key:
            self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize the Gemini client with the API key."""
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(self.model)
            self.logger.info(f"Gemini client initialized with model: {self.model}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini client: {e}")
            self._client = None

    async def _generate_impl(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> str:
        """
        Generate text using the Gemini API.

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
                "Gemini client not initialized. Check API key.",
                provider=self.provider_name,
                retryable=False,
            )

        try:
            # Combine system prompt and user prompt
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"

            # Configure generation parameters
            generation_config = {}
            if "temperature" in kwargs:
                generation_config["temperature"] = kwargs["temperature"]
            if "max_tokens" in kwargs:
                generation_config["max_output_tokens"] = kwargs["max_tokens"]

            # Generate response
            response = await self._client.generate_content_async(
                full_prompt,
                generation_config=generation_config if generation_config else None,
            )

            if response.text:
                return response.text

            # Handle blocked responses
            if hasattr(response, "prompt_feedback"):
                feedback = response.prompt_feedback
                if hasattr(feedback, "block_reason"):
                    raise AIClientError(
                        f"Content blocked: {feedback.block_reason}",
                        provider=self.provider_name,
                        retryable=False,
                    )

            raise AIClientError(
                "Empty response from Gemini",
                provider=self.provider_name,
                retryable=True,
            )

        except AIClientError:
            raise
        except Exception as e:
            error_message = str(e).lower()
            # Check for rate limiting
            if "rate" in error_message or "quota" in error_message:
                raise AIClientError(
                    f"Rate limit exceeded: {e}",
                    provider=self.provider_name,
                    retryable=True,
                )
            # Check for API key issues
            if "api key" in error_message or "unauthorized" in error_message:
                raise AIClientError(
                    f"API key error: {e}",
                    provider=self.provider_name,
                    retryable=False,
                )
            # Generic error
            raise AIClientError(
                f"Gemini API error: {e}",
                provider=self.provider_name,
                retryable=True,
            )

    def is_available(self) -> bool:
        """
        Check if the Gemini client is available.

        Returns:
            bool: True if the client is properly configured.
        """
        return bool(self.api_key and self._client)
