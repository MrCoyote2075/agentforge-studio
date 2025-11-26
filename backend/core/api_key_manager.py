"""
AgentForge Studio - API Key Manager.

This module provides a manager for handling multiple API keys per provider
with various rotation strategies and automatic failover.
"""

import logging
import os
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class RotationStrategy(str, Enum):
    """Enumeration of available key rotation strategies."""

    ROUND_ROBIN = "round_robin"
    LEAST_USED = "least_used"
    FAILOVER = "failover"
    LOAD_BALANCE = "load_balance"


@dataclass
class KeyStats:
    """Statistics for a single API key."""

    key_id: str
    usage_count: int = 0
    error_count: int = 0
    rate_limit_count: int = 0
    last_used: datetime | None = None
    last_error: datetime | None = None
    is_available: bool = True
    cooldown_until: datetime | None = None

    def record_usage(self) -> None:
        """Record a successful usage of this key."""
        self.usage_count += 1
        self.last_used = datetime.utcnow()

    def record_error(self, is_rate_limit: bool = False) -> None:
        """Record an error for this key."""
        self.error_count += 1
        self.last_error = datetime.utcnow()
        if is_rate_limit:
            self.rate_limit_count += 1

    def mark_unavailable(self, cooldown_seconds: int = 60) -> None:
        """Mark this key as temporarily unavailable."""
        self.is_available = False
        cooldown = datetime.utcnow()
        self.cooldown_until = cooldown + timedelta(seconds=cooldown_seconds)

    def check_availability(self) -> bool:
        """Check if the key is available (cooldown has passed)."""
        if self.is_available:
            return True
        if self.cooldown_until and datetime.utcnow() > self.cooldown_until:
            self.is_available = True
            self.cooldown_until = None
            return True
        return False


@dataclass
class ProviderKeys:
    """Holds keys and stats for a single provider."""

    provider_name: str
    keys: list[str] = field(default_factory=list)
    stats: dict[str, KeyStats] = field(default_factory=dict)
    current_index: int = 0

    def add_key(self, key: str, key_id: str) -> None:
        """Add a new API key with its identifier."""
        if key and key not in self.keys:
            self.keys.append(key)
            self.stats[key_id] = KeyStats(key_id=key_id)

    def has_keys(self) -> bool:
        """Check if any keys are available."""
        return len(self.keys) > 0


class APIKeyManager:
    """
    Manager for multiple API keys per provider.

    Supports various rotation strategies and automatic failover when a key
    encounters errors or rate limits.

    Attributes:
        strategy: The rotation strategy to use.
        providers: Dictionary of provider keys.

    Example:
        >>> manager = APIKeyManager(strategy=RotationStrategy.ROUND_ROBIN)
        >>> key = manager.get_key("openai")
        >>> manager.record_usage("openai", key)
    """

    # Supported providers and their environment variable patterns
    SUPPORTED_PROVIDERS = ["openai", "gemini", "anthropic"]
    MAX_KEYS_PER_PROVIDER = 2

    def __init__(
        self,
        strategy: RotationStrategy = RotationStrategy.ROUND_ROBIN,
        cooldown_seconds: int = 60,
    ) -> None:
        """
        Initialize the API Key Manager.

        Args:
            strategy: The rotation strategy to use.
            cooldown_seconds: Seconds to cool down a key after failure.
        """
        self._strategy = strategy
        self._cooldown_seconds = cooldown_seconds
        self._providers: dict[str, ProviderKeys] = {}
        self.logger = logging.getLogger("api_key_manager")
        self._load_keys_from_environment()

    def _load_keys_from_environment(self) -> None:
        """Load API keys from environment variables."""
        for provider in self.SUPPORTED_PROVIDERS:
            provider_keys = ProviderKeys(provider_name=provider)
            provider_upper = provider.upper()

            # Load primary key (e.g., OPENAI_API_KEY)
            primary_key = os.getenv(f"{provider_upper}_API_KEY", "")
            if primary_key:
                provider_keys.add_key(primary_key, f"{provider}_key_primary")

            # Load numbered keys (e.g., OPENAI_API_KEY_1, OPENAI_API_KEY_2)
            for i in range(1, self.MAX_KEYS_PER_PROVIDER + 1):
                key = os.getenv(f"{provider_upper}_API_KEY_{i}", "")
                if key:
                    provider_keys.add_key(key, f"{provider}_key_{i}")

            self._providers[provider] = provider_keys

    @property
    def strategy(self) -> RotationStrategy:
        """Get the current rotation strategy."""
        return self._strategy

    @strategy.setter
    def strategy(self, value: RotationStrategy) -> None:
        """Set the rotation strategy."""
        self._strategy = value
        self.logger.info(f"Rotation strategy changed to: {value}")

    def get_key(self, provider: str) -> str | None:
        """
        Get an API key for the specified provider.

        The key is selected based on the current rotation strategy.

        Args:
            provider: The provider name (openai, gemini, anthropic).

        Returns:
            str | None: The selected API key or None if no keys available.
        """
        provider = provider.lower()
        if provider not in self._providers:
            self.logger.warning(f"Unknown provider: {provider}")
            return None

        provider_keys = self._providers[provider]
        if not provider_keys.has_keys():
            self.logger.warning(f"No keys available for provider: {provider}")
            return None

        # Refresh availability status for all keys
        for key_id, stats in provider_keys.stats.items():
            stats.check_availability()

        # Get available keys
        available_keys = [
            (key, key_id)
            for key, key_id in zip(
                provider_keys.keys, list(provider_keys.stats.keys())
            )
            if provider_keys.stats[key_id].is_available
        ]

        if not available_keys:
            self.logger.warning(f"All keys for {provider} are in cooldown")
            # Return the first key anyway as a fallback
            return provider_keys.keys[0] if provider_keys.keys else None

        selected_key = self._select_key_by_strategy(provider_keys, available_keys)
        return selected_key

    def _select_key_by_strategy(
        self,
        provider_keys: ProviderKeys,
        available_keys: list[tuple[str, str]],
    ) -> str:
        """
        Select a key based on the current strategy.

        Args:
            provider_keys: The provider's key configuration.
            available_keys: List of (key, key_id) tuples that are available.

        Returns:
            str: The selected API key.
        """
        if self._strategy == RotationStrategy.ROUND_ROBIN:
            # Cycle through keys in order
            index = provider_keys.current_index % len(available_keys)
            provider_keys.current_index = (provider_keys.current_index + 1) % len(
                available_keys
            )
            return available_keys[index][0]

        elif self._strategy == RotationStrategy.LEAST_USED:
            # Select the key with the lowest usage count
            min_usage = min(
                provider_keys.stats[key_id].usage_count
                for _, key_id in available_keys
            )
            for key, key_id in available_keys:
                if provider_keys.stats[key_id].usage_count == min_usage:
                    return key
            return available_keys[0][0]

        elif self._strategy == RotationStrategy.FAILOVER:
            # Use the first available key, only switch on failure
            return available_keys[0][0]

        elif self._strategy == RotationStrategy.LOAD_BALANCE:
            # Random selection for load balancing
            return random.choice(available_keys)[0]

        # Default to first key
        return available_keys[0][0]

    def record_usage(self, provider: str, key: str) -> None:
        """
        Record a successful usage of an API key.

        Args:
            provider: The provider name.
            key: The API key that was used.
        """
        provider = provider.lower()
        if provider not in self._providers:
            return

        provider_keys = self._providers[provider]
        if key not in provider_keys.keys:
            return

        key_index = provider_keys.keys.index(key)
        stats_keys = list(provider_keys.stats.keys())
        if key_index < len(stats_keys):
            target_key_id = stats_keys[key_index]
            provider_keys.stats[target_key_id].record_usage()

    def record_error(
        self,
        provider: str,
        key: str,
        is_rate_limit: bool = False,
        mark_unavailable: bool = True,
    ) -> None:
        """
        Record an error for an API key.

        Args:
            provider: The provider name.
            key: The API key that failed.
            is_rate_limit: Whether the error was a rate limit.
            mark_unavailable: Whether to mark the key as unavailable.
        """
        provider = provider.lower()
        if provider not in self._providers:
            return

        provider_keys = self._providers[provider]
        if key not in provider_keys.keys:
            return

        key_index = provider_keys.keys.index(key)
        stats_keys = list(provider_keys.stats.keys())
        if key_index < len(stats_keys):
            target_key_id = stats_keys[key_index]
            stats = provider_keys.stats[target_key_id]
            stats.record_error(is_rate_limit)
            if mark_unavailable:
                stats.mark_unavailable(self._cooldown_seconds)
            self.logger.warning(
                f"Recorded error for {provider} key {target_key_id}: "
                f"total errors={stats.error_count}, "
                f"rate limits={stats.rate_limit_count}"
            )

    def get_next_available_key(self, provider: str, failed_key: str) -> str | None:
        """
        Get the next available key after a failure.

        This is used for automatic failover when a key encounters an error.

        Args:
            provider: The provider name.
            failed_key: The key that just failed.

        Returns:
            str | None: The next available key, or None if no keys available.
        """
        provider = provider.lower()
        if provider not in self._providers:
            return None

        provider_keys = self._providers[provider]
        if not provider_keys.has_keys():
            return None

        # Get keys other than the failed one
        other_keys = [k for k in provider_keys.keys if k != failed_key]
        if not other_keys:
            return None

        # Find an available key
        for key in other_keys:
            key_index = provider_keys.keys.index(key)
            key_id = list(provider_keys.stats.keys())[key_index]
            if provider_keys.stats[key_id].check_availability():
                return key

        return None

    def get_stats(self, provider: str | None = None) -> dict[str, Any]:
        """
        Get usage statistics for one or all providers.

        Args:
            provider: Optional provider name. If None, returns stats for all.

        Returns:
            dict: Statistics for the requested provider(s).
        """
        if provider:
            provider = provider.lower()
            if provider not in self._providers:
                return {}
            provider_keys = self._providers[provider]
            return {
                "provider": provider,
                "total_keys": len(provider_keys.keys),
                "keys": {
                    key_id: {
                        "usage_count": stats.usage_count,
                        "error_count": stats.error_count,
                        "rate_limit_count": stats.rate_limit_count,
                        "is_available": stats.check_availability(),
                        "last_used": (
                            stats.last_used.isoformat() if stats.last_used else None
                        ),
                    }
                    for key_id, stats in provider_keys.stats.items()
                },
            }

        # Return stats for all providers
        return {
            p: self.get_stats(p)
            for p in self._providers
            if self._providers[p].has_keys()
        }

    def get_available_providers(self) -> list[str]:
        """
        Get list of providers with at least one key configured.

        Returns:
            list[str]: List of provider names.
        """
        return [
            provider
            for provider, keys in self._providers.items()
            if keys.has_keys()
        ]

    def reset_stats(self, provider: str | None = None) -> None:
        """
        Reset statistics for one or all providers.

        Args:
            provider: Optional provider name. If None, resets all.
        """
        if provider:
            provider = provider.lower()
            if provider in self._providers:
                for key_id in self._providers[provider].stats:
                    self._providers[provider].stats[key_id] = KeyStats(key_id=key_id)
                self._providers[provider].current_index = 0
        else:
            for p in self._providers:
                self.reset_stats(p)

    def __repr__(self) -> str:
        """Return a string representation of the manager."""
        providers_info = ", ".join(
            f"{p}:{len(self._providers[p].keys)}"
            for p in self._providers
            if self._providers[p].has_keys()
        )
        return (
            f"APIKeyManager(strategy={self._strategy.value}, "
            f"providers=[{providers_info}])"
        )
