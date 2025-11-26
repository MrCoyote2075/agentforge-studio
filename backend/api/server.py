"""
FastAPI Server module for AgentForge Studio.

This module provides the main FastAPI application instance and
server configuration.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import get_config
from backend.api.routes import router
from backend.api.websocket import websocket_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.
    
    Handles startup and shutdown events for the application.
    
    Args:
        app: The FastAPI application instance.
        
    Yields:
        None
    """
    # Startup
    config = get_config()
    app.state.config = config
    
    # Initialize message bus
    from backend.core.message_bus import MessageBus
    app.state.message_bus = MessageBus()
    await app.state.message_bus.start()
    
    # Initialize workspace manager
    from backend.core.workspace_manager import WorkspaceManager
    app.state.workspace_manager = WorkspaceManager(
        config.workspace_dir
    )
    
    yield
    
    # Shutdown
    await app.state.message_bus.stop()


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance.
    """
    config = get_config()
    
    app = FastAPI(
        title=config.app_name,
        description="AI-Powered Website Builder API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(router, prefix="/api/v1")
    app.include_router(websocket_router, prefix="/ws")
    
    return app


# Create the default application instance
app = create_app()


@app.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint.
    
    Returns:
        Welcome message.
    """
    return {
        "message": "Welcome to AgentForge Studio API",
        "docs": "/docs",
        "version": "0.1.0"
    }


@app.get("/health")
async def health_check() -> dict[str, str]:
    """
    Health check endpoint.
    
    Returns:
        Health status.
    """
    return {"status": "healthy"}
