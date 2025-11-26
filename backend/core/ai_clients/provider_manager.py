"""
AgentForge Studio - Provider Manager.

This module manages multiple AI providers with fallback support.
"""

import logging

from backend.core.ai_clients.anthropic_client import AnthropicClient
from backend.core.ai_clients.base_client import AIClientError, BaseAIClient
from backend.core.ai_clients.gemini_client import GeminiClient
from backend.core.ai_clients.openai_client import OpenAIClient
from backend.core.config import get_settings


class ProviderManager:
    """
    Manages multiple AI providers with fallback support.

    This class handles registration and selection of AI providers,
    automatically falling back to secondary providers if the primary
    provider fails.

    Attributes:
        providers: Dictionary of registered providers by name.
        priority_order: List of provider names in priority order.
        default_provider: Name of the default provider.
        logger: Logger instance for this manager.

    Example:
        >>> manager = ProviderManager()
        >>> manager.register_provider("gemini", GeminiClient())
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
        self.default_provider = default_provider
        self.logger = logging.getLogger("ai_client.provider_manager")

        # Auto-configure from settings
        self._auto_configure()

    def _auto_configure(self) -> None:
        """Auto-configure providers based on available API keys."""
        settings = get_settings()

        # Register available providers in priority order
        if settings.gemini_api_key:
            self.register_provider("gemini", GeminiClient())
        if settings.openai_api_key:
            self.register_provider("openai", OpenAIClient())
        if settings.anthropic_api_key:
            self.register_provider("anthropic", AnthropicClient())

        # Set default provider if not specified
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
        Generate text using available providers with fallback.

        Args:
            prompt: The user prompt.
            system_prompt: Optional system prompt for context.
            provider: Specific provider to use (skips fallback).
            fallback: Whether to fall back to other providers on failure.
            **kwargs: Additional parameters for generation.

        Returns:
            Tuple of (generated text, provider name used).

        Raises:
            AIClientError: If all providers fail.
        """
        if not self.providers:
            raise AIClientError(
                "No AI providers configured. Check API keys in environment.",
                provider="none",
                retryable=False,
            )

        # If specific provider requested, use only that one
        if provider:
            client = self.providers.get(provider)
            if not client:
                raise AIClientError(
                    f"Provider '{provider}' not available",
                    provider=provider,
                    retryable=False,
                )
            result = await client.generate(prompt, system_prompt, **kwargs)
            return result, provider

        # Try providers in priority order
        errors = []
        providers_to_try = self.priority_order if fallback else [self.default_provider]

        for provider_name in providers_to_try:
            if provider_name not in self.providers:
                continue

            client = self.providers[provider_name]
            if not client.is_available():
                continue

            try:
                self.logger.debug(f"Trying provider: {provider_name}")
                result = await client.generate(prompt, system_prompt, **kwargs)
                return result, provider_name
            except AIClientError as e:
                self.logger.warning(f"Provider '{provider_name}' failed: {e}")
                errors.append((provider_name, str(e)))
                if not fallback:
                    raise

        # All providers failed
        error_details = "; ".join(f"{p}: {e}" for p, e in errors)
        raise AIClientError(
            f"All providers failed. Errors: {error_details}",
            provider="all",
            retryable=False,
        )

    async def generate_code(
        self,
        prompt: str,
        language: str = "python",
        provider: str | None = None,
        fallback: bool = True,
        **kwargs,
    ) -> tuple[str, str]:
        """
        Generate code using available providers with fallback.

        Args:
            prompt: Description of the code to generate.
            language: Programming language.
            provider: Specific provider to use.
            fallback: Whether to fall back to other providers on failure.
            **kwargs: Additional parameters for generation.

        Returns:
            Tuple of (generated code, provider name used).

        Raises:
            AIClientError: If all providers fail.
        """
        if not self.providers:
            raise AIClientError(
                "No AI providers configured. Check API keys in environment.",
                provider="none",
                retryable=False,
            )

        # If specific provider requested, use only that one
        if provider:
            client = self.providers.get(provider)
            if not client:
                raise AIClientError(
                    f"Provider '{provider}' not available",
                    provider=provider,
                    retryable=False,
                )
            result = await client.generate_code(prompt, language, **kwargs)
            return result, provider

        # Try providers in priority order
        errors = []
        providers_to_try = self.priority_order if fallback else [self.default_provider]

        for provider_name in providers_to_try:
            if provider_name not in self.providers:
                continue

            client = self.providers[provider_name]
            if not client.is_available():
                continue

            try:
                self.logger.debug(f"Trying provider for code: {provider_name}")
                result = await client.generate_code(prompt, language, **kwargs)
                return result, provider_name
            except AIClientError as e:
                self.logger.warning(f"Provider '{provider_name}' failed: {e}")
                errors.append((provider_name, str(e)))
                if not fallback:
                    raise

        # All providers failed
        error_details = "; ".join(f"{p}: {e}" for p, e in errors)
        raise AIClientError(
            f"All providers failed. Errors: {error_details}",
            provider="all",
            retryable=False,
        )

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
        return f"ProviderManager(providers={available}, default={self.default_provider})"
