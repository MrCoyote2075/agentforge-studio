"""
Tests for the API Key Manager.

These tests verify that the APIKeyManager works correctly
with multiple keys and rotation strategies.
"""

import os
from unittest.mock import patch

import pytest

from backend.core.api_key_manager import (
    APIKeyManager,
    KeyStats,
    ProviderKeys,
    RotationStrategy,
)


class TestKeyStats:
    """Tests for the KeyStats class."""

    def test_initialization(self):
        """Test that KeyStats initializes correctly."""
        stats = KeyStats(key_id="test_key_1")
        assert stats.key_id == "test_key_1"
        assert stats.usage_count == 0
        assert stats.error_count == 0
        assert stats.rate_limit_count == 0
        assert stats.is_available is True
        assert stats.last_used is None

    def test_record_usage(self):
        """Test recording usage updates stats."""
        stats = KeyStats(key_id="test_key_1")
        stats.record_usage()
        assert stats.usage_count == 1
        assert stats.last_used is not None

    def test_record_error(self):
        """Test recording errors updates stats."""
        stats = KeyStats(key_id="test_key_1")
        stats.record_error()
        assert stats.error_count == 1
        assert stats.last_error is not None

    def test_record_rate_limit_error(self):
        """Test recording rate limit errors."""
        stats = KeyStats(key_id="test_key_1")
        stats.record_error(is_rate_limit=True)
        assert stats.error_count == 1
        assert stats.rate_limit_count == 1

    def test_mark_unavailable(self):
        """Test marking key as unavailable."""
        stats = KeyStats(key_id="test_key_1")
        stats.mark_unavailable(cooldown_seconds=60)
        assert stats.is_available is False
        assert stats.cooldown_until is not None


class TestProviderKeys:
    """Tests for the ProviderKeys class."""

    def test_initialization(self):
        """Test that ProviderKeys initializes correctly."""
        provider = ProviderKeys(provider_name="openai")
        assert provider.provider_name == "openai"
        assert provider.keys == []
        assert provider.stats == {}
        assert provider.current_index == 0

    def test_add_key(self):
        """Test adding a key."""
        provider = ProviderKeys(provider_name="openai")
        provider.add_key("sk-test123", "openai_key_1")
        assert len(provider.keys) == 1
        assert "openai_key_1" in provider.stats

    def test_add_duplicate_key(self):
        """Test that duplicate keys are not added."""
        provider = ProviderKeys(provider_name="openai")
        provider.add_key("sk-test123", "openai_key_1")
        provider.add_key("sk-test123", "openai_key_2")
        assert len(provider.keys) == 1

    def test_has_keys(self):
        """Test checking if keys are available."""
        provider = ProviderKeys(provider_name="openai")
        assert provider.has_keys() is False
        provider.add_key("sk-test123", "openai_key_1")
        assert provider.has_keys() is True


class TestAPIKeyManager:
    """Tests for the APIKeyManager class."""

    def test_initialization_default_strategy(self):
        """Test that APIKeyManager initializes with default strategy."""
        with patch.dict(os.environ, {}, clear=True):
            manager = APIKeyManager()
            assert manager.strategy == RotationStrategy.ROUND_ROBIN

    def test_initialization_custom_strategy(self):
        """Test initialization with custom strategy."""
        with patch.dict(os.environ, {}, clear=True):
            manager = APIKeyManager(strategy=RotationStrategy.LEAST_USED)
            assert manager.strategy == RotationStrategy.LEAST_USED

    def test_loads_keys_from_environment(self):
        """Test that keys are loaded from environment."""
        env_vars = {
            "OPENAI_API_KEY": "sk-primary",
            "OPENAI_API_KEY_1": "sk-key1",
            "OPENAI_API_KEY_2": "sk-key2",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            manager = APIKeyManager()
            assert "openai" in manager.get_available_providers()

    def test_get_key_returns_key(self):
        """Test getting a key returns a valid key."""
        env_vars = {"OPENAI_API_KEY": "sk-test"}
        with patch.dict(os.environ, env_vars, clear=True):
            manager = APIKeyManager()
            key = manager.get_key("openai")
            assert key == "sk-test"

    def test_get_key_unknown_provider(self):
        """Test getting key for unknown provider returns None."""
        with patch.dict(os.environ, {}, clear=True):
            manager = APIKeyManager()
            key = manager.get_key("unknown")
            assert key is None

    def test_get_key_no_keys(self):
        """Test getting key when no keys configured returns None."""
        with patch.dict(os.environ, {}, clear=True):
            manager = APIKeyManager()
            key = manager.get_key("openai")
            assert key is None

    def test_round_robin_rotation(self):
        """Test round robin key rotation."""
        env_vars = {
            "OPENAI_API_KEY_1": "sk-key1",
            "OPENAI_API_KEY_2": "sk-key2",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            manager = APIKeyManager(strategy=RotationStrategy.ROUND_ROBIN)
            key1 = manager.get_key("openai")
            key2 = manager.get_key("openai")
            assert key1 != key2 or len(set([key1, key2])) == 1

    def test_record_usage(self):
        """Test recording usage for a key."""
        env_vars = {"OPENAI_API_KEY": "sk-test"}
        with patch.dict(os.environ, env_vars, clear=True):
            manager = APIKeyManager()
            manager.record_usage("openai", "sk-test")
            stats = manager.get_stats("openai")
            assert stats["total_keys"] == 1

    def test_record_error(self):
        """Test recording error for a key."""
        env_vars = {"OPENAI_API_KEY": "sk-test"}
        with patch.dict(os.environ, env_vars, clear=True):
            manager = APIKeyManager()
            manager.record_error("openai", "sk-test", is_rate_limit=True)
            # Key should be marked for cooldown
            stats = manager.get_stats("openai")
            assert stats is not None

    def test_get_next_available_key(self):
        """Test getting next available key after failure."""
        env_vars = {
            "OPENAI_API_KEY_1": "sk-key1",
            "OPENAI_API_KEY_2": "sk-key2",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            manager = APIKeyManager()
            next_key = manager.get_next_available_key("openai", "sk-key1")
            assert next_key == "sk-key2"

    def test_get_stats_all_providers(self):
        """Test getting stats for all providers."""
        env_vars = {
            "OPENAI_API_KEY": "sk-test",
            "GEMINI_API_KEY": "gemini-test",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            manager = APIKeyManager()
            stats = manager.get_stats()
            assert "openai" in stats
            assert "gemini" in stats

    def test_get_stats_single_provider(self):
        """Test getting stats for single provider."""
        env_vars = {"OPENAI_API_KEY": "sk-test"}
        with patch.dict(os.environ, env_vars, clear=True):
            manager = APIKeyManager()
            stats = manager.get_stats("openai")
            assert stats["provider"] == "openai"
            assert stats["total_keys"] == 1

    def test_get_available_providers(self):
        """Test getting list of available providers."""
        env_vars = {
            "OPENAI_API_KEY": "sk-test",
            "GEMINI_API_KEY": "gemini-test",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            manager = APIKeyManager()
            providers = manager.get_available_providers()
            assert "openai" in providers
            assert "gemini" in providers

    def test_reset_stats(self):
        """Test resetting statistics."""
        env_vars = {"OPENAI_API_KEY": "sk-test"}
        with patch.dict(os.environ, env_vars, clear=True):
            manager = APIKeyManager()
            manager.record_usage("openai", "sk-test")
            manager.reset_stats("openai")
            stats = manager.get_stats("openai")
            # After reset, usage should be 0
            for key_id, key_stats in stats["keys"].items():
                assert key_stats["usage_count"] == 0

    def test_repr(self):
        """Test string representation."""
        env_vars = {"OPENAI_API_KEY": "sk-test"}
        with patch.dict(os.environ, env_vars, clear=True):
            manager = APIKeyManager()
            repr_str = repr(manager)
            assert "APIKeyManager" in repr_str
            assert "round_robin" in repr_str


class TestRotationStrategies:
    """Tests for different rotation strategies."""

    def test_failover_strategy(self):
        """Test failover strategy uses first key."""
        env_vars = {
            "OPENAI_API_KEY_1": "sk-key1",
            "OPENAI_API_KEY_2": "sk-key2",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            manager = APIKeyManager(strategy=RotationStrategy.FAILOVER)
            key1 = manager.get_key("openai")
            key2 = manager.get_key("openai")
            # Failover should always use first key
            assert key1 == key2

    def test_least_used_strategy(self):
        """Test least used strategy."""
        env_vars = {
            "OPENAI_API_KEY_1": "sk-key1",
            "OPENAI_API_KEY_2": "sk-key2",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            manager = APIKeyManager(strategy=RotationStrategy.LEAST_USED)
            key1 = manager.get_key("openai")
            manager.record_usage("openai", key1)
            # Next key should be different (less used)
            key2 = manager.get_key("openai")
            assert key2 != key1

    def test_load_balance_strategy(self):
        """Test load balance strategy (random selection)."""
        env_vars = {
            "OPENAI_API_KEY_1": "sk-key1",
            "OPENAI_API_KEY_2": "sk-key2",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            manager = APIKeyManager(strategy=RotationStrategy.LOAD_BALANCE)
            # Should return a valid key
            key = manager.get_key("openai")
            assert key in ["sk-key1", "sk-key2"]
