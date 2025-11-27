"""
AgentForge Studio - Configuration Management.

This module handles loading environment variables and managing
application settings.
"""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    This class uses Pydantic's BaseSettings to automatically load
    configuration from environment variables with type validation.

    Attributes:
        gemini_api_key_1: Google Gemini API key 1 (primary).
        gemini_api_key_2: Google Gemini API key 2 (secondary).
        api_host: Host to run the API server on.
        api_port: Port to run the API server on.
        preview_port: Port for the preview server.
        workspace_path: Path to store workspace files.
        output_path: Path to store output files.

    Example:
        >>> settings = get_settings()
        >>> print(settings.api_port)
        8000
    """

    # Gemini API Keys (Load Balanced)
    gemini_api_key_1: str = Field(
        default="",
        description="Google Gemini API key 1 (primary)",
    )
    gemini_api_key_2: str = Field(
        default="",
        description="Google Gemini API key 2 (secondary)",
    )

    # AI Provider Configuration
    default_ai_provider: str = Field(
        default="gemini",
        description="Default AI provider (only gemini supported)",
    )
    api_key_strategy: str = Field(
        default="load_balance",
        description="Strategy for key rotation (round-robin between keys)",
    )
    gemini_model: str = Field(
        default="gemini-1.5-pro",
        description="Gemini model to use",
    )

    # Server Configuration
    api_host: str = Field(
        default="localhost",
        description="Host for the API server",
    )
    api_port: int = Field(
        default=8000,
        description="Port for the API server",
    )
    preview_port: int = Field(
        default=8080,
        description="Port for the preview server",
    )

    # Paths
    workspace_path: Path = Field(
        default=Path("./workspaces"),
        description="Path to workspace directory",
    )
    output_path: Path = Field(
        default=Path("./outputs"),
        description="Path to output directory",
    )

    # Application Settings
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )
    max_concurrent_agents: int = Field(
        default=10,
        description="Maximum number of concurrent agent operations",
    )

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

    def ensure_directories(self) -> None:
        """Ensure that required directories exist."""
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        self.output_path.mkdir(parents=True, exist_ok=True)

    def get_workspace_dir(self, project_id: str) -> Path:
        """
        Get the workspace directory for a specific project.

        Args:
            project_id: The project identifier.

        Returns:
            Path to the project's workspace directory.
        """
        return self.workspace_path / project_id

    def get_output_dir(self, project_id: str) -> Path:
        """
        Get the output directory for a specific project.

        Args:
            project_id: The project identifier.

        Returns:
            Path to the project's output directory.
        """
        return self.output_path / project_id

    def has_ai_credentials(self) -> bool:
        """
        Check if at least one Gemini API key is configured.

        Returns:
            bool: True if at least one API key is set.
        """
        return bool(self.gemini_api_key_1 or self.gemini_api_key_2)

    def get_available_providers(self) -> list[str]:
        """
        Get list of AI providers with configured API keys.

        Returns:
            List of available provider names.
        """
        providers = []
        if self.gemini_api_key_1 or self.gemini_api_key_2:
            providers.append("gemini")
        return providers


@lru_cache
def get_settings() -> Settings:
    """
    Get the application settings singleton.

    This function is cached to ensure only one Settings instance
    is created throughout the application lifecycle.

    Returns:
        Settings: The application settings instance.

    Example:
        >>> settings = get_settings()
        >>> print(settings.api_host)
        localhost
    """
    return Settings()


def reload_settings() -> Settings:
    """
    Reload settings from environment.

    Clears the cached settings and returns a fresh instance.
    Useful for testing or when environment changes.

    Returns:
        Settings: Fresh settings instance.
    """
    get_settings.cache_clear()
    return get_settings()
