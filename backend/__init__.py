"""
AgentForge Studio Backend Package.

AI-Powered Software Development Agency - A backend service that orchestrates
specialized AI agents to automate website building.
"""

__version__ = "0.1.0"
__author__ = "AgentForge Studio Team"

from backend.core.config import get_settings

__all__ = ["__version__", "__author__", "get_settings"]
