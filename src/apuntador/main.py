"""
Main FastAPI application entry point.

This module creates the FastAPI application using the application factory
pattern for clean separation of concerns.
"""

from apuntador import __version__
from apuntador.application import create_app
from apuntador.config import get_settings
from apuntador.core.logging import intercept_standard_logging
from apuntador.infrastructure.factory import InfrastructureFactory
from apuntador.middleware import MTLSValidationMiddleware

# Intercept logs from uvicorn and other libraries
intercept_standard_logging()

# Create FastAPI application using factory
app = create_app()

# Add mTLS validation middleware (after app creation to access settings)
settings = get_settings()
infrastructure_factory = InfrastructureFactory.from_settings(settings)
app.add_middleware(
    MTLSValidationMiddleware,
    infrastructure_factory=infrastructure_factory,
)

# Configure docs endpoints based on settings
if not settings.enable_docs:
    app.docs_url = None
    app.redoc_url = None
    app.openapi_url = None


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "message": "Apuntador OAuth Backend",
        "version": __version__,
        "docs": "/docs" if settings.enable_docs else None,
    }


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
