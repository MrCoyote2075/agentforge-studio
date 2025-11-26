"""
Tests for AI Client implementations.

These tests verify that the AI clients work correctly,
using mocks to avoid actual API calls during testing.
"""

from unittest.mock import MagicMock, patch

import pytest

from backend.core.ai_clients.anthropic_client import AnthropicClient
from backend.core.ai_clients.base_client import AIClientError, BaseAIClient
from backend.core.ai_clients.gemini_client import GeminiClient
from backend.core.ai_clients.openai_client import OpenAIClient
from backend.core.ai_clients.provider_manager import ProviderManager


# Paths for patching
GEMINI_SETTINGS = "backend.core.ai_clients.gemini_client.get_settings"
OPENAI_SETTINGS = "backend.core.ai_clients.openai_client.get_settings"
ANTHROPIC_SETTINGS = "backend.core.ai_clients.anthropic_client.get_settings"
PROVIDER_SETTINGS = "backend.core.ai_clients.provider_manager.get_settings"


class TestBaseAIClient:
    """Tests for the BaseAIClient abstract class."""

    def test_cannot_instantiate_directly(self):
        """Test that BaseAIClient cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseAIClient("test", "test-model")


class TestGeminiClient:
    """Tests for the GeminiClient."""

    def test_initialization_without_api_key(self):
        """Test client is not available without API key."""
        with patch(GEMINI_SETTINGS) as mock_settings:
            mock_settings.return_value.gemini_api_key = ""
            client = GeminiClient()
            assert not client.is_available()

    def test_initialization_with_api_key(self):
        """Test that client initializes with API key."""
        with patch(GEMINI_SETTINGS) as mock_settings:
            mock_settings.return_value.gemini_api_key = "test-key"
            with patch("google.generativeai.configure"):
                with patch("google.generativeai.GenerativeModel") as m:
                    m.return_value = MagicMock()
                    client = GeminiClient(api_key="test-key")
                    assert client.api_key == "test-key"

    @pytest.mark.asyncio
    async def test_generate_raises_error_without_client(self):
        """Test that generate raises error when client not initialized."""
        with patch(GEMINI_SETTINGS) as mock_settings:
            mock_settings.return_value.gemini_api_key = ""
            client = GeminiClient()
            with pytest.raises(AIClientError) as exc_info:
                await client.generate("test prompt")
            assert "not initialized" in str(exc_info.value).lower()


class TestOpenAIClient:
    """Tests for the OpenAIClient."""

    def test_initialization_without_api_key(self):
        """Test client is not available without API key."""
        with patch(OPENAI_SETTINGS) as mock_settings:
            mock_settings.return_value.openai_api_key = ""
            client = OpenAIClient()
            assert not client.is_available()

    def test_initialization_with_api_key(self):
        """Test that client initializes with API key."""
        with patch(OPENAI_SETTINGS) as mock_settings:
            mock_settings.return_value.openai_api_key = "test-key"
            with patch("openai.AsyncOpenAI") as mock_openai:
                mock_openai.return_value = MagicMock()
                client = OpenAIClient(api_key="test-key")
                assert client.api_key == "test-key"

    @pytest.mark.asyncio
    async def test_generate_raises_error_without_client(self):
        """Test that generate raises error when client not initialized."""
        with patch(OPENAI_SETTINGS) as mock_settings:
            mock_settings.return_value.openai_api_key = ""
            client = OpenAIClient()
            with pytest.raises(AIClientError) as exc_info:
                await client.generate("test prompt")
            assert "not initialized" in str(exc_info.value).lower()


class TestAnthropicClient:
    """Tests for the AnthropicClient."""

    def test_initialization_without_api_key(self):
        """Test client is not available without API key."""
        with patch(ANTHROPIC_SETTINGS) as mock_settings:
            mock_settings.return_value.anthropic_api_key = ""
            client = AnthropicClient()
            assert not client.is_available()

    def test_initialization_with_api_key(self):
        """Test that client initializes with API key."""
        with patch(ANTHROPIC_SETTINGS) as mock_settings:
            mock_settings.return_value.anthropic_api_key = "test-key"
            with patch("anthropic.AsyncAnthropic") as mock_anthropic:
                mock_anthropic.return_value = MagicMock()
                client = AnthropicClient(api_key="test-key")
                assert client.api_key == "test-key"

    @pytest.mark.asyncio
    async def test_generate_raises_error_without_client(self):
        """Test that generate raises error when client not initialized."""
        with patch(ANTHROPIC_SETTINGS) as mock_settings:
            mock_settings.return_value.anthropic_api_key = ""
            client = AnthropicClient()
            with pytest.raises(AIClientError) as exc_info:
                await client.generate("test prompt")
            assert "not initialized" in str(exc_info.value).lower()


class TestProviderManager:
    """Tests for the ProviderManager."""

    def test_initialization_without_api_keys(self):
        """Test manager with no providers when no keys set."""
        with patch(PROVIDER_SETTINGS) as mock_settings:
            mock_settings.return_value.gemini_api_key = ""
            mock_settings.return_value.openai_api_key = ""
            mock_settings.return_value.anthropic_api_key = ""
            manager = ProviderManager()
            assert not manager.has_available_provider()
            assert len(manager.get_available_providers()) == 0

    def test_get_available_providers(self):
        """Test getting list of available providers."""
        with patch(PROVIDER_SETTINGS) as mock_settings:
            mock_settings.return_value.gemini_api_key = ""
            mock_settings.return_value.openai_api_key = ""
            mock_settings.return_value.anthropic_api_key = ""
            manager = ProviderManager()
            providers = manager.get_available_providers()
            assert isinstance(providers, list)

    @pytest.mark.asyncio
    async def test_generate_raises_error_without_providers(self):
        """Test that generate raises error when no providers available."""
        with patch(PROVIDER_SETTINGS) as mock_settings:
            mock_settings.return_value.gemini_api_key = ""
            mock_settings.return_value.openai_api_key = ""
            mock_settings.return_value.anthropic_api_key = ""
            manager = ProviderManager()
            with pytest.raises(AIClientError) as exc_info:
                await manager.generate("test prompt")
            assert "no ai providers configured" in str(exc_info.value).lower()

    def test_repr(self):
        """Test string representation of manager."""
        with patch(PROVIDER_SETTINGS) as mock_settings:
            mock_settings.return_value.gemini_api_key = ""
            mock_settings.return_value.openai_api_key = ""
            mock_settings.return_value.anthropic_api_key = ""
            manager = ProviderManager()
            repr_str = repr(manager)
            assert "ProviderManager" in repr_str


class TestAIClientError:
    """Tests for the AIClientError exception."""

    def test_error_attributes(self):
        """Test that error has correct attributes."""
        error = AIClientError("Test error", provider="test", retryable=True)
        assert str(error) == "Test error"
        assert error.provider == "test"
        assert error.retryable is True

    def test_error_default_retryable(self):
        """Test that retryable defaults to False."""
        error = AIClientError("Test error", provider="test")
        assert error.retryable is False
