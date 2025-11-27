"""
AgentForge Studio - Provider Manager.

This module manages Gemini AI provider with load-balanced keys.
"""

import logging

from backend.core.ai_clients.base_client import AIClientError, BaseAIClient
from backend.core.ai_clients.gemini_client import GeminiClient
from backend.core.config import get_settings


class ProviderManager:
    """
    Manages Gemini AI provider with load-balanced keys.

    This class handles Gemini provider configuration with dual key
    support for load balancing.

    Attributes:
        providers: Dictionary of registered providers by name.
        priority_order: List of provider names in priority order.
        default_provider: Name of the default provider.
        logger: Logger instance for this manager.

    Example:
        >>> manager = ProviderManager()
        >>> response = await manager.generate("Hello!")
    """

    def __init__(self, default_provider: str | None = None) -> None:
        """
        Initialize the provider manager.

        Args:
            default_provider: Name of the default provider to use.
        """
        self.providers: dict[str, BaseAIClient] = {}
        self.priority_order: list[str] = []
        self.default_provider = default_provider or "gemini"
        self.logger = logging.getLogger("ai_client.provider_manager")
        self._current_key_index = 0

        # Auto-configure from settings
        self._auto_configure()

    def _auto_configure(self) -> None:
        """Auto-configure Gemini provider with load-balanced keys."""
        settings = get_settings()

        # Get both Gemini keys
        key1 = settings.gemini_api_key_1
        key2 = settings.gemini_api_key_2

        # Use the first available key for initialization
        primary_key = key1 or key2
        if primary_key:
            self.register_provider("gemini", GeminiClient(api_key=primary_key))
            self._gemini_keys = [k for k in [key1, key2] if k]
        else:
            self._gemini_keys = []

        # Set default provider
        if not self.default_provider and self.priority_order:
            self.default_provider = self.priority_order[0]

    def register_provider(
        self,
        name: str,
        client: BaseAIClient,
        priority: int | None = None,
    ) -> None:
        """
        Register an AI provider.

        Args:
            name: Name for the provider.
            client: The AI client instance.
            priority: Optional priority position (lower = higher priority).
        """
        if not client.is_available():
            self.logger.warning(f"Provider '{name}' is not available (check API key)")
            return

        self.providers[name] = client

        # Add to priority order
        if name not in self.priority_order:
            if priority is not None and 0 <= priority <= len(self.priority_order):
                self.priority_order.insert(priority, name)
            else:
                self.priority_order.append(name)

        self.logger.info(f"Registered provider: {name}")

    def _get_next_gemini_key(self) -> str | None:
        """
        Get the next Gemini key using round-robin load balancing.

        Returns:
            str | None: The next API key or None if no keys available.
        """
        if not self._gemini_keys:
            return None
        key = self._gemini_keys[self._current_key_index % len(self._gemini_keys)]
        self._current_key_index = (self._current_key_index + 1) % len(self._gemini_keys)
        return key

    def get_provider(self, name: str | None = None) -> BaseAIClient | None:
        """
        Get a specific provider by name or the default provider.

        Args:
            name: Optional provider name. Uses default if not specified.

        Returns:
            The AI client or None if not found.
        """
        provider_name = name or self.default_provider
        if provider_name:
            return self.providers.get(provider_name)
        return None

    def get_available_providers(self) -> list[str]:
        """
        Get list of available provider names.

        Returns:
            List of provider names in priority order.
        """
        return [
            name for name in self.priority_order
            if name in self.providers and self.providers[name].is_available()
        ]

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        provider: str | None = None,
        fallback: bool = True,
        **kwargs,
    ) -> tuple[str, str]:
        """
        Generate text using Gemini with load-balanced keys.

        Args:
            prompt: The user prompt.
            system_prompt: Optional system prompt for context.
            provider: Specific provider to use (only gemini supported).
            fallback: Whether to try alternate keys on failure.
            **kwargs: Additional parameters for generation.

        Returns:
            Tuple of (generated text, provider name used).

        Raises:
            AIClientError: If generation fails.
        """
        if not self.providers:
            raise AIClientError(
                "No AI providers configured. Check Gemini API keys in environment.",
                provider="none",
                retryable=False,
            )

        # Get load-balanced Gemini key
        api_key = self._get_next_gemini_key()
        if not api_key:
            raise AIClientError(
                "No Gemini API keys configured",
                provider="gemini",
                retryable=False,
            )

        client = self.providers.get("gemini")
        if not client:
            raise AIClientError(
                "Gemini provider not available",
                provider="gemini",
                retryable=False,
            )

        # Create a new client with the load-balanced key
        from backend.core.ai_clients.gemini_client import GeminiClient
        lb_client = GeminiClient(api_key=api_key)

        if not lb_client.is_available():
            raise AIClientError(
                "Gemini provider is not properly configured",
                provider="gemini",
                retryable=False,
            )

        try:
            self.logger.debug("Using Gemini with load-balanced key")
            result = await lb_client.generate(prompt, system_prompt, **kwargs)
            return result, "gemini"
        except AIClientError as e:
            self.logger.warning(f"Gemini generation failed: {e}")
            # Try with alternate key if available and fallback is enabled
            if fallback and len(self._gemini_keys) > 1:
                alt_key = self._get_next_gemini_key()
                if alt_key and alt_key != api_key:
                    self.logger.debug("Retrying with alternate Gemini key")
                    alt_client = GeminiClient(api_key=alt_key)
                    if alt_client.is_available():
                        try:
                            result = await alt_client.generate(
                                prompt, system_prompt, **kwargs
                            )
                            return result, "gemini"
                        except AIClientError:
                            pass
            raise

    async def generate_code(
        self,
        prompt: str,
        language: str = "python",
        provider: str | None = None,
        fallback: bool = True,
        **kwargs,
    ) -> tuple[str, str]:
        """
        Generate code using Gemini with load-balanced keys.

        Args:
            prompt: Description of the code to generate.
            language: Programming language.
            provider: Specific provider to use (only gemini supported).
            fallback: Whether to try alternate keys on failure.
            **kwargs: Additional parameters for generation.

        Returns:
            Tuple of (generated code, provider name used).

        Raises:
            AIClientError: If generation fails.
        """
        if not self.providers:
            raise AIClientError(
                "No AI providers configured. Check Gemini API keys in environment.",
                provider="none",
                retryable=False,
            )

        # Get load-balanced Gemini key
        api_key = self._get_next_gemini_key()
        if not api_key:
            raise AIClientError(
                "No Gemini API keys configured",
                provider="gemini",
                retryable=False,
            )

        # Create a new client with the load-balanced key
        from backend.core.ai_clients.gemini_client import GeminiClient
        lb_client = GeminiClient(api_key=api_key)

        if not lb_client.is_available():
            raise AIClientError(
                "Gemini provider is not properly configured",
                provider="gemini",
                retryable=False,
            )

        try:
            self.logger.debug("Using Gemini for code generation with load-balanced key")
            result = await lb_client.generate_code(prompt, language, **kwargs)
            return result, "gemini"
        except AIClientError as e:
            self.logger.warning(f"Gemini code generation failed: {e}")
            # Try with alternate key if available and fallback is enabled
            if fallback and len(self._gemini_keys) > 1:
                alt_key = self._get_next_gemini_key()
                if alt_key and alt_key != api_key:
                    self.logger.debug("Retrying with alternate Gemini key")
                    alt_client = GeminiClient(api_key=alt_key)
                    if alt_client.is_available():
                        try:
                            result = await alt_client.generate_code(
                                prompt, language, **kwargs
                            )
                            return result, "gemini"
                        except AIClientError:
                            pass
            raise

    def has_available_provider(self) -> bool:
        """
        Check if at least one provider is available.

        Returns:
            bool: True if at least one provider is available.
        """
        return any(
            client.is_available()
            for client in self.providers.values()
        )

    def __repr__(self) -> str:
        """Return a string representation of the manager."""
        available = self.get_available_providers()
        return (
            f"ProviderManager(providers={available}, "
            f"default={self.default_provider})"
        )
