"""
AgentForge Studio - Main Entry Point.

This module serves as the primary entry point for the AgentForge Studio
application. It initializes the API server and starts all necessary services.
"""

import asyncio
import logging
import sys
from typing import NoReturn

import uvicorn

from backend.api.server import create_app
from backend.core.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def main() -> NoReturn:
    """
    Main entry point for AgentForge Studio.

    Initializes the FastAPI application and starts the Uvicorn server
    with the configured host and port settings.

    Returns:
        NoReturn: This function runs indefinitely until interrupted.
    """
    settings = get_settings()

    logger.info("Starting AgentForge Studio...")
    logger.info(f"API Server: http://{settings.api_host}:{settings.api_port}")
    logger.info(f"Preview Server: http://{settings.api_host}:{settings.preview_port}")

    # Create the FastAPI application
    app = create_app()

    # Run the server
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level="info",
    )


async def async_main() -> None:
    """
    Async entry point for programmatic usage.

    This function can be used when running the application
    within an existing async context.
    """
    settings = get_settings()

    logger.info("Starting AgentForge Studio (async mode)...")

    config = uvicorn.Config(
        create_app(),
        host=settings.api_host,
        port=settings.api_port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    main()
