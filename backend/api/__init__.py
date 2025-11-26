"""
API package for AgentForge Studio.

This package contains the FastAPI server, routes, and WebSocket
handlers for the application.
"""

from backend.api.server import create_app, app
from backend.api.routes import router
from backend.api.websocket import WebSocketManager

__all__ = [
    "create_app",
    "app",
    "router",
    "WebSocketManager",
]
