"""
Main FastAPI application entry point.

This module creates the FastAPI application using the application factory
pattern for clean separation of concerns.
"""

from apuntador.application import create_app
from apuntador.app_setup import add_root_endpoint, setup_app
from apuntador.config import get_settings
from apuntador.core.logging import intercept_standard_logging

# Intercept logs from uvicorn and other libraries
intercept_standard_logging()

# Create FastAPI application using factory
app = create_app()

# Setup middleware and configuration
setup_app(app)

# Add root endpoint
add_root_endpoint(app)


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning",
    )
