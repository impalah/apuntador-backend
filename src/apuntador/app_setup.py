"""
Application setup utilities.

Provides common setup functions for both main.py and lambda_main.py
to avoid code duplication.
"""

from fastapi import FastAPI

from apuntador import __version__
from apuntador.config import get_settings
from apuntador.infrastructure.factory import InfrastructureFactory
from apuntador.middleware import MTLSValidationMiddleware


def setup_app(app: FastAPI) -> None:
    """
    Configure the FastAPI application with middleware and routes.

    Args:
        app: FastAPI application instance to configure
    """
    # Add mTLS validation middleware
    settings = get_settings()
    infrastructure_factory = InfrastructureFactory.from_settings(settings)
    app.add_middleware(
        MTLSValidationMiddleware,
        infrastructure_factory=infrastructure_factory,
    )


def add_root_endpoint(app: FastAPI) -> None:
    """
    Add root endpoint to the application.

    Args:
        app: FastAPI application instance
    """
    settings = get_settings()

    @app.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint with API information."""
        return {
            "message": "Apuntador OAuth Backend",
            "version": __version__,
            "docs": "/docs" if settings.enable_docs else None,
        }
