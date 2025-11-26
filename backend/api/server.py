"""
AgentForge Studio - API Server.

This module creates and configures the FastAPI application
with all routes, middleware, and WebSocket support.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router
from backend.api.websocket import websocket_router
from backend.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Handles startup and shutdown events for the application.

    Args:
        app: The FastAPI application instance.

    Yields:
        None during the application's lifespan.
    """
    # Startup
    settings = get_settings()
    settings.ensure_directories()

    # TODO: Initialize message bus
    # TODO: Initialize agents
    # TODO: Start preview server if configured

    yield

    # Shutdown
    # TODO: Cleanup resources
    # TODO: Stop agents
    # TODO: Close message bus connections


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI: The configured application instance.

    Example:
        >>> app = create_app()
        >>> # Use with uvicorn
    """
    settings = get_settings()

    app = FastAPI(
        title="AgentForge Studio",
        description="AI-Powered Software Development Agency API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routers
    app.include_router(router, prefix="/api")
    app.include_router(websocket_router)

    # Root health check
    @app.get("/", tags=["health"])
    async def root() -> dict:
        """
        Root endpoint - health check.

        Returns:
            dict: Service status information.
        """
        return {
            "service": "AgentForge Studio",
            "status": "healthy",
            "version": "0.1.0",
        }

    @app.get("/health", tags=["health"])
    async def health_check() -> dict:
        """
        Health check endpoint.

        Returns:
            dict: Detailed health status.
        """
        return {
            "status": "healthy",
            "api": "running",
            "ai_providers": settings.get_available_providers(),
            "has_credentials": settings.has_ai_credentials(),
        }

    return app
