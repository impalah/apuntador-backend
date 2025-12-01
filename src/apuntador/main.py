"""
Main FastAPI application entry point.

This module creates the FastAPI application using the application factory
pattern for clean separation of concerns.
"""

from apuntador.application import create_app
from apuntador.app_setup import add_root_endpoint, setup_app
from apuntador.config import get_settings
from apuntador.core.logging import intercept_standard_logging

# Configure OpenTelemetry BEFORE anything else (optional, only if dependencies installed)
try:
    from apuntador.core.telemetry import (
        configure_opentelemetry,
        instrument_fastapi,
        instrument_httpx,
        instrument_logging,
    )
    
    # Initialize OpenTelemetry with AWS X-Ray integration
    configure_opentelemetry(
        service_name="apuntador-backend",
        service_version="1.0.0",  # Update from settings if available
        environment=get_settings().environment if hasattr(get_settings(), "environment") else "development",
    )
    
    # Instrument logging BEFORE configuring loguru
    instrument_logging()
    
    # Instrument HTTPX client for outgoing requests
    instrument_httpx()
    
    OTEL_ENABLED = True
except ImportError:
    # OpenTelemetry not installed, continue without it
    OTEL_ENABLED = False

# Intercept logs from uvicorn and other libraries
intercept_standard_logging()

# Create FastAPI application using factory
app = create_app()

# Instrument FastAPI with OpenTelemetry (if enabled)
if OTEL_ENABLED:
    instrument_fastapi(app)

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
