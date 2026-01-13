"""
Application lifecycle management.

Handles startup and shutdown events for the FastAPI application.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Handles startup and shutdown events for the application.

    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info(" Starting apuntador backend...")
    logger.info(f"Application version: {app.version}")

    # TODO: Initialize database connections
    # TODO: Load CA certificates
    # TODO: Initialize infrastructure factory

    yield

    # Shutdown
    logger.info(" Shutting down apuntador backend...")

    # TODO: Close database connections
    # TODO: Cleanup resources
