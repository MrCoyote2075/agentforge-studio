"""
Configuration module for AgentForge Studio.

This module provides configuration management for the application.
"""

import os
from typing import Any, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    """
    Application configuration settings.
    
    Attributes:
        app_name: Name of the application.
        debug: Whether debug mode is enabled.
        host: Server host address.
        port: Server port number.
        workspace_dir: Directory for workspaces.
        log_level: Logging level.
        openai_api_key: OpenAI API key for AI services.
        database_url: Database connection URL.
        cors_origins: Allowed CORS origins.
    """
    app_name: str = "AgentForge Studio"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    workspace_dir: str = "./workspaces"
    log_level: str = "INFO"
    openai_api_key: Optional[str] = None
    database_url: Optional[str] = None
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    
    @classmethod
    def from_env(cls) -> "Config":
        """
        Create configuration from environment variables.
        
        Returns:
            Config instance populated from environment.
        """
        cors_origins_str = os.getenv("CORS_ORIGINS", "*")
        cors_origins = [
            origin.strip() 
            for origin in cors_origins_str.split(",")
        ]
        
        return cls(
            app_name=os.getenv("APP_NAME", "AgentForge Studio"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            workspace_dir=os.getenv("WORKSPACE_DIR", "./workspaces"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            database_url=os.getenv("DATABASE_URL"),
            cors_origins=cors_origins
        )
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.
        
        Args:
            key: The configuration key.
            default: Default value if key not found.
            
        Returns:
            The configuration value.
        """
        return getattr(self, key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: The configuration key.
            value: The value to set.
        """
        if hasattr(self, key):
            setattr(self, key, value)
    
    def get_workspace_path(self) -> Path:
        """
        Get the workspace directory as a Path object.
        
        Returns:
            Path to the workspace directory.
        """
        return Path(self.workspace_dir).resolve()
    
    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate the configuration.
        
        Returns:
            Tuple of (is_valid, list of error messages).
        """
        errors: list[str] = []
        
        if self.port < 1 or self.port > 65535:
            errors.append(f"Invalid port number: {self.port}")
        
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            errors.append(f"Invalid log level: {self.log_level}")
        
        return len(errors) == 0, errors


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """
    Get the global configuration instance.
    
    Returns:
        The global Config instance.
    """
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def set_config(config: Config) -> None:
    """
    Set the global configuration instance.
    
    Args:
        config: The Config instance to set.
    """
    global _config
    _config = config
