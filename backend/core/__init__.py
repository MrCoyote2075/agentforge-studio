"""
Core package for AgentForge Studio.

This package contains core utilities and services used by the
AI-powered website builder.
"""

from backend.core.config import Config, get_config
from backend.core.message_bus import MessageBus
from backend.core.workspace_manager import WorkspaceManager

__all__ = [
    "Config",
    "get_config",
    "MessageBus",
    "WorkspaceManager",
]
